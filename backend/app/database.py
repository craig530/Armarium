from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from pathlib import Path
from .config import settings


def _ensure_db_dir():
    url = settings.database_url
    if "sqlite" in url:
        path_part = url.replace("sqlite+aiosqlite:///", "")
        db_path = Path(path_part)
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_db_dir()

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

# An in-memory SQLite DB is per-connection — without StaticPool, each checkout
# from the default pool would get its own empty database.
engine_kwargs = {"echo": False, "connect_args": connect_args}
if settings.database_url.endswith(":memory:"):
    engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(settings.database_url, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


if "sqlite" in settings.database_url:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):
        # WAL allows readers and writers to proceed concurrently instead of
        # blocking on a single file lock — important once the catalogue and
        # its background cover-fetch tasks are both hitting the DB.
        # NORMAL is safe under WAL (only durability of the last commit after
        # an OS crash is at risk, not corruption).
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        # SQLite ignores FK constraints (ON DELETE SET NULL/CASCADE, etc.) by
        # default — without this, declared `ForeignKey(..., ondelete=...)`
        # behaviour is purely documentation.
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
