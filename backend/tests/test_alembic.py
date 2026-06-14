"""Tests for the Alembic baseline migration against a real file-based SQLite DB."""
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.main import ALEMBIC_INI

EXPECTED_TABLES = {
    "alembic_version",
    "locations",
    "media_subtypes",
    "platforms",
    "users",
    "media_items",
    "plex_config",
    "plex_library_mappings",
    "item_links",
}


@pytest.fixture
def tmp_sqlite_url():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield f"sqlite:///{db_path}"


def _upgrade(url: str) -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def test_upgrade_head_creates_schema_and_seeds_subtypes(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            assert EXPECTED_TABLES.issubset(tables)

            subtypes = conn.execute(
                text("SELECT name, category, supertype, sort_order FROM media_subtypes ORDER BY id")
            ).fetchall()
    finally:
        engine.dispose()

    assert len(subtypes) == 10
    assert ("CD", "MUSIC", "PHYSICAL", 0) in subtypes
    assert ("Audiobook", "BOOKS", "DIGITAL", 1) in subtypes


def test_upgrade_head_is_idempotent(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM media_subtypes")).scalar()
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    finally:
        engine.dispose()

    assert count == 10
    assert version == "0001"
