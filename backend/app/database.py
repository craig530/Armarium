from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
