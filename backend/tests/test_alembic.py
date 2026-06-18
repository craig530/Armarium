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
    "item_lists",
    "media_item_lists",
    "scheduled_jobs",
    "app_config",
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

    assert len(subtypes) == 16
    assert ("CD", "MUSIC", "PHYSICAL", 0) in subtypes
    assert ("Audiobook", "BOOKS", "DIGITAL", 1) in subtypes
    assert ("Nintendo Switch", "GAMES", "PHYSICAL", 0) in subtypes
    assert ("PlayStation Store", "GAMES", "DIGITAL", 2) in subtypes


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

    assert count == 16
    assert version == "0008"


def test_upgrade_head_adds_rating_columns(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            columns = {col["name"] for col in inspect(conn).get_columns("media_items")}
    finally:
        engine.dispose()

    assert {"tmdb_rating", "user_rating"}.issubset(columns)


def test_upgrade_head_adds_lists_tables_and_permission(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            user_columns = {col["name"] for col in inspect(conn).get_columns("users")}
    finally:
        engine.dispose()

    assert {"item_lists", "media_item_lists"}.issubset(tables)
    assert "can_manage_lists" in user_columns


def test_upgrade_head_adds_games_columns(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            columns = {col["name"] for col in inspect(conn).get_columns("media_items")}
    finally:
        engine.dispose()

    assert {"developer", "igdb_id"}.issubset(columns)


def test_upgrade_head_adds_scheduled_jobs_and_schedule_columns(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            user_columns = {col["name"] for col in inspect(conn).get_columns("users")}
            mapping_columns = {col["name"] for col in inspect(conn).get_columns("plex_library_mappings")}
    finally:
        engine.dispose()

    assert "scheduled_jobs" in tables
    assert "can_manage_schedules" in user_columns
    assert {
        "last_sync_status",
        "last_sync_created",
        "last_sync_updated",
        "last_sync_removed",
        "last_sync_error",
    }.issubset(mapping_columns)


def test_upgrade_head_adds_plex_rating_key_and_machine_identifier(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            media_columns = {col["name"] for col in inspect(conn).get_columns("media_items")}
            plex_columns = {col["name"] for col in inspect(conn).get_columns("plex_config")}
    finally:
        engine.dispose()

    assert "plex_rating_key" in media_columns
    assert "machine_identifier" in plex_columns


def test_upgrade_head_adds_ownership(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            user_columns = {col["name"] for col in inspect(conn).get_columns("users")}
            media_columns = {col["name"] for col in inspect(conn).get_columns("media_items")}
            list_columns = {col["name"] for col in inspect(conn).get_columns("item_lists")}
            mapping_columns = {col["name"] for col in inspect(conn).get_columns("plex_library_mappings")}
            tables = set(inspect(conn).get_table_names())

            shared = conn.execute(
                text("SELECT id, is_system, is_active FROM users WHERE username = 'shared'")
            ).fetchone()
            ownership_mode = conn.execute(
                text("SELECT ownership_mode FROM app_config WHERE id = 1")
            ).scalar()
    finally:
        engine.dispose()

    assert "is_system" in user_columns
    assert "owner_id" in media_columns
    assert "owner_id" in list_columns
    assert "owner_id" in mapping_columns
    assert "app_config" in tables

    assert shared is not None, "shared system user should be seeded"
    assert shared[1] == 1, "is_system should be True"
    assert shared[2] == 0, "is_active should be False"

    assert ownership_mode == "shared"


def test_upgrade_head_adds_disabled_categories(tmp_sqlite_url):
    _upgrade(tmp_sqlite_url)

    engine = create_engine(tmp_sqlite_url)
    try:
        with engine.connect() as conn:
            config_columns = {col["name"] for col in inspect(conn).get_columns("app_config")}
            disabled = conn.execute(
                text("SELECT disabled_categories FROM app_config WHERE id = 1")
            ).scalar()
    finally:
        engine.dispose()

    assert "disabled_categories" in config_columns
    assert disabled == "[]"
