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
from app.database import Base
from app.migrations import (
    run_additive_migrations,
    create_missing_indexes,
    add_location_sort_order_column,
    drop_plex_source_columns,
    reset_mismatched_plex_tables,
    _MISSING_INDEXES,
)
from app.services.search import setup_fts, _fts_columns_from_sql, FTS_COLUMNS


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


async def test_create_missing_indexes_adds_new_columns():
    # media_subtype_id and platform_id gained index=True after media_items
    # already existed in the wild — confirm they're covered.
    assert ("media_items", "media_subtype_id") in _MISSING_INDEXES
    assert ("media_items", "platform_id") in _MISSING_INDEXES

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Simulate an upgraded database where create_all (on an older
            # model) never created these indexes.
            for table_name, column_name in _MISSING_INDEXES:
                await conn.execute(text(f'DROP INDEX IF EXISTS "ix_{table_name}_{column_name}"'))

            await create_missing_indexes(conn)

            for table_name, column_name in _MISSING_INDEXES:
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=:name"
                ), {"name": f"ix_{table_name}_{column_name}"})
                assert result.first() is not None, f"missing index ix_{table_name}_{column_name}"
    finally:
        await engine.dispose()


async def test_sqlite_foreign_keys_pragma_enabled():
    # Declared `ForeignKey(..., ondelete=...)` behaviour (SET NULL/CASCADE)
    # is unenforced unless this pragma is set on every connection.
    from app.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        assert result.scalar() == 1


async def test_add_location_sort_order_column():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # Simulate an older on-disk schema that predates `sort_order`.
            await conn.execute(text(
                "CREATE TABLE locations ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(200) NOT NULL, "
                "parent_id INTEGER"
                ")"
            ))
            await conn.execute(text("INSERT INTO locations (id, name) VALUES (1, 'Shelf')"))

            before = await conn.execute(text('PRAGMA table_info("locations")'))
            assert "sort_order" not in {row[1] for row in before.fetchall()}

            await add_location_sort_order_column(conn)

            after = await conn.execute(text('PRAGMA table_info("locations")'))
            assert "sort_order" in {row[1] for row in after.fetchall()}

            # Existing rows backfill to the default rather than NULL.
            result = await conn.execute(text("SELECT sort_order FROM locations WHERE id = 1"))
            assert result.scalar() == 0

            # Re-running on an already-migrated database is a no-op.
            await add_location_sort_order_column(conn)
    finally:
        await engine.dispose()


async def test_drop_plex_source_columns():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # Simulate an older on-disk schema that predates removal of
            # `source`/`source_id`.
            await conn.execute(text(
                "CREATE TABLE media_items ("
                "id INTEGER PRIMARY KEY, "
                "title VARCHAR(500) NOT NULL, "
                "source VARCHAR(20), "
                "source_id VARCHAR(200)"
                ")"
            ))
            await conn.execute(text(
                "INSERT INTO media_items (id, title, source, source_id) "
                "VALUES (1, 'The Matrix', 'plex', '1:plex://movie/matrix')"
            ))

            before = await conn.execute(text('PRAGMA table_info("media_items")'))
            before_columns = {row[1] for row in before.fetchall()}
            assert "source" in before_columns
            assert "source_id" in before_columns

            await drop_plex_source_columns(conn)

            after = await conn.execute(text('PRAGMA table_info("media_items")'))
            after_columns = {row[1] for row in after.fetchall()}
            assert "source" not in after_columns
            assert "source_id" not in after_columns

            # Existing rows survive with their other data intact.
            result = await conn.execute(text("SELECT title FROM media_items WHERE id = 1"))
            assert result.scalar() == "The Matrix"

            # Re-running on an already-migrated database is a no-op.
            await drop_plex_source_columns(conn)
    finally:
        await engine.dispose()


async def test_reset_mismatched_plex_tables_recreates_outdated_schema():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # Simulate the pre-Phase-3 schema: `plex_config` predates
            # `platform_id` (now required), and `plex_library_mappings` still
            # has the `platform_id` column that moved to `plex_config`.
            await conn.execute(text(
                "CREATE TABLE plex_config ("
                "id INTEGER PRIMARY KEY, "
                "base_url VARCHAR(500) NOT NULL, "
                "token VARCHAR(500) NOT NULL, "
                "enabled BOOLEAN NOT NULL DEFAULT 0, "
                "created_at DATETIME, "
                "updated_at DATETIME"
                ")"
            ))
            await conn.execute(text(
                "CREATE TABLE plex_library_mappings ("
                "id INTEGER PRIMARY KEY, "
                "section_key VARCHAR(50) NOT NULL UNIQUE, "
                "section_title VARCHAR(300) NOT NULL, "
                "section_type VARCHAR(20) NOT NULL, "
                "category VARCHAR(20) NOT NULL, "
                "platform_id INTEGER NOT NULL, "
                "last_synced_at DATETIME, "
                "created_at DATETIME, "
                "updated_at DATETIME"
                ")"
            ))

            await reset_mismatched_plex_tables(conn)
            await conn.run_sync(Base.metadata.create_all)

            config_columns = {row[1] for row in (await conn.execute(
                text('PRAGMA table_info("plex_config")')
            )).fetchall()}
            mapping_columns = {row[1] for row in (await conn.execute(
                text('PRAGMA table_info("plex_library_mappings")')
            )).fetchall()}
    finally:
        await engine.dispose()

    assert "platform_id" in config_columns
    assert "platform_id" not in mapping_columns


async def test_reset_mismatched_plex_tables_leaves_missing_nullable_column_for_additive_migration():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # Simulate an install where `plex_library_mappings` has every
            # current column except the nullable `last_synced_at` — added in
            # a later release. This must NOT be treated as an irreparable
            # mismatch (no orphaned columns, nothing NOT NULL is missing).
            await conn.execute(text(
                "CREATE TABLE plex_library_mappings ("
                "id INTEGER PRIMARY KEY, "
                "section_key VARCHAR(50) NOT NULL UNIQUE, "
                "section_title VARCHAR(300) NOT NULL, "
                "section_type VARCHAR(20) NOT NULL, "
                "category VARCHAR(20) NOT NULL, "
                "created_at DATETIME, "
                "updated_at DATETIME"
                ")"
            ))
            await conn.execute(text(
                "INSERT INTO plex_library_mappings "
                "(id, section_key, section_title, section_type, category) "
                "VALUES (1, 'abc', 'Movies', 'movie', 'films_tv')"
            ))

            await reset_mismatched_plex_tables(conn)

            # Table was left in place — row survives.
            result = await conn.execute(text(
                "SELECT section_title FROM plex_library_mappings WHERE id = 1"
            ))
            assert result.scalar() == "Movies"

            await run_additive_migrations(conn)

            after = await conn.execute(text('PRAGMA table_info("plex_library_mappings")'))
            assert "last_synced_at" in {row[1] for row in after.fetchall()}

            result = await conn.execute(text(
                "SELECT section_title FROM plex_library_mappings WHERE id = 1"
            ))
            assert result.scalar() == "Movies"
    finally:
        await engine.dispose()


async def test_reset_mismatched_plex_tables_is_noop_when_schema_matches():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("INSERT INTO platforms (id, name) VALUES (1, 'Plex')"))
            await conn.execute(text(
                "INSERT INTO plex_config (id, base_url, token, enabled, platform_id) "
                "VALUES (1, 'https://plex.example.com', 'token', 0, 1)"
            ))

            await reset_mismatched_plex_tables(conn)

            result = await conn.execute(text("SELECT base_url FROM plex_config WHERE id = 1"))
            assert result.scalar() == "https://plex.example.com"
    finally:
        await engine.dispose()


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
