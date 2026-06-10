import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import settings
from .database import engine, Base, AsyncSessionLocal
from .migrations import run_additive_migrations
from .api.v1.router import router
from . import models  # noqa: F401 — registers ORM classes before create_all

logger = logging.getLogger("armarium")


async def _ensure_admin():
    """Create the default admin account if no users exist."""
    from .models.user import User
    from .services.auth import hash_password

    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(User))).scalars().first()
        if count is None:
            admin = User(
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                is_admin=True,
            )
            db.add(admin)
            await db.commit()
            if settings.admin_password == "changeme":
                logger.warning(
                    "⚠️  Default admin password in use — set ADMIN_PASSWORD in .env before exposing to network."
                )
            else:
                logger.info("Created admin user: %s", settings.admin_username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await run_additive_migrations(conn)

    Path(settings.covers_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.backup_dir).mkdir(parents=True, exist_ok=True)

    await _ensure_admin()
    yield


app = FastAPI(
    title="Armarium API",
    description="Self-hosted media catalogue — CDs, DVDs, Blu-rays & Books",
    version="1.0.0",
    lifespan=lifespan,
)

# Bearer-token auth doesn't rely on cookies, so allow_credentials is left off —
# combining it with a wildcard origin is both unnecessary and rejected by browsers.
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

covers_dir = Path(settings.covers_dir)
covers_dir.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=str(covers_dir)), name="covers")


@app.get("/health", tags=["system"])
async def health():
    from .services.cache import lookup_cache
    return {"status": "ok", "version": "1.0.0", "cache_entries": lookup_cache.size()}
