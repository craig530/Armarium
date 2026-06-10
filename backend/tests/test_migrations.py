"""Tests for the additive startup migration in app.migrations."""
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
from app.migrations import run_additive_migrations


async def test_adds_missing_nullable_columns():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # Simulate an older on-disk schema that predates several columns
            # the current MediaItem model defines.
            await conn.execute(text(
                "CREATE TABLE media_items ("
                "id INTEGER PRIMARY KEY, "
                "title VARCHAR(500) NOT NULL, "
                "media_type VARCHAR(10) NOT NULL"
                ")"
            ))

            before = await conn.execute(text('PRAGMA table_info("media_items")'))
            before_columns = {row[1] for row in before.fetchall()}
            assert "barcode" not in before_columns
            assert "notes" not in before_columns

            await run_additive_migrations(conn)

            after = await conn.execute(text('PRAGMA table_info("media_items")'))
            after_columns = {row[1] for row in after.fetchall()}
    finally:
        await engine.dispose()

    assert "barcode" in after_columns
    assert "notes" in after_columns
    assert "location_id" in after_columns
    # Pre-existing columns are untouched.
    assert "title" in after_columns
    assert "media_type" in after_columns


async def test_skips_tables_that_dont_exist_yet():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # No tables created — create_all() runs first in normal startup;
            # this just confirms the migration step doesn't error on an
            # empty database.
            await run_additive_migrations(conn)
    finally:
        await engine.dispose()
