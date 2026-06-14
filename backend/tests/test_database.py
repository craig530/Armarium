"""Tests for app.database engine configuration."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
os.environ.setdefault("COVERS_DIR", "/tmp/armarium_test_covers")
os.environ.setdefault("BACKUP_DIR", "/tmp/armarium_test_backups")

from sqlalchemy import text


async def test_sqlite_foreign_keys_pragma_enabled():
    # Declared `ForeignKey(..., ondelete=...)` behaviour (SET NULL/CASCADE/
    # RESTRICT) is unenforced unless this pragma is set on every connection.
    from app.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        assert result.scalar() == 1
