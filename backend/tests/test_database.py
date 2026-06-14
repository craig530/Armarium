"""Tests for app.database engine configuration."""
from sqlalchemy import text


async def test_sqlite_foreign_keys_pragma_enabled():
    # Declared `ForeignKey(..., ondelete=...)` behaviour (SET NULL/CASCADE/
    # RESTRICT) is unenforced unless this pragma is set on every connection.
    from app.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        assert result.scalar() == 1
