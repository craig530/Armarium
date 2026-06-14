"""Tests for app.services.search (FTS5 setup)."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
os.environ.setdefault("COVERS_DIR", "/tmp/armarium_test_covers")
os.environ.setdefault("BACKUP_DIR", "/tmp/armarium_test_backups")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401 — registers ORM tables on Base.metadata
from app.database import Base
from app.services.search import setup_fts, _fts_columns_from_sql, FTS_COLUMNS


async def test_setup_fts_rebuilds_when_column_set_changes():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Simulate a pre-existing FTS table indexing an older, smaller
            # column set (as it would be before FTS_COLUMNS was extended).
            old_columns = ["title", "artist", "author", "director", "genres", "description"]
            await conn.execute(text(
                f"CREATE VIRTUAL TABLE media_items_fts USING fts5("
                f"{', '.join(old_columns)}, content='media_items', content_rowid='id')"
            ))

            await setup_fts(conn)

            result = await conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='media_items_fts'")
            )
            rebuilt_sql = result.scalar()
    finally:
        await engine.dispose()

    assert _fts_columns_from_sql(rebuilt_sql) == set(FTS_COLUMNS)
