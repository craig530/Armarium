import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base, AsyncSessionLocal
from .repositories.user import UserRepository
from .services.media_subtypes import seed_default_media_subtypes
from .services.search import setup_fts
from .api.v1.router import router
from . import models  # noqa: F401 — registers ORM classes before create_all

logger = logging.getLogger("armarium")

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _run_alembic_upgrade(sync_conn) -> None:
    """Bring a file-based database to the latest Alembic revision, using the
    connection already opened by the async engine (see env.py's
    `config.attributes["connection"]` branch — no second engine/event loop)."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["connection"] = sync_conn
    command.upgrade(cfg, "head")


async def _ensure_admin():
    """Create the default admin account if no users exist."""
    from .models.user import User
    from .services.auth import hash_password

    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        if not await repo.any_exist():
            admin = User(
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                is_admin=True,
            )
            repo.add(admin)
            await repo.commit()
            if settings.admin_password == "changeme":
                logger.warning(
                    "⚠️  Default admin password in use — set ADMIN_PASSWORD in .env before exposing to network."
                )
            else:
                logger.info("Created admin user: %s", settings.admin_username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.endswith(":memory:"):
        # In-memory test DBs skip Alembic entirely — this is schema-equivalent
        # to the v1 baseline by construction (both derive from Base.metadata).
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        async with engine.connect() as conn:
            await conn.run_sync(_run_alembic_upgrade)
            await conn.commit()

    async with engine.begin() as conn:
        await setup_fts(conn)

    Path(settings.covers_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.backup_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.location_icons_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.platform_logos_dir).mkdir(parents=True, exist_ok=True)

    if settings.database_url.endswith(":memory:"):
        # The Alembic baseline seeds these for file-based DBs; in-memory test
        # DBs need the same seed data applied directly.
        async with AsyncSessionLocal() as db:
            await seed_default_media_subtypes(db)

    await _ensure_admin()
    yield


app = FastAPI(
    title="Armarium API",
    description="Self-hosted media catalogue — Music, Films & TV and Books, physical or digital",
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

# Compresses JSON list/search responses, which dominate traffic for a
# catalogue with thousands of items. Excludes the static image mounts below:
# JPEGs are already compressed (gzip adds nothing), and GZipMiddleware
# rewrites Content-Length/body for *any* response — including 206 Partial
# Content from StaticFiles range requests — without adjusting Content-Range,
# producing a response some proxies (e.g. Cloudflare) treat as invalid or
# incomplete.
class AssetExemptGZipMiddleware(GZipMiddleware):
    EXEMPT_PREFIXES = ("/covers/", "/location-icons/", "/platform-logos/")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith(self.EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


app.add_middleware(AssetExemptGZipMiddleware, minimum_size=500)

app.include_router(router)

covers_dir = Path(settings.covers_dir)
covers_dir.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=str(covers_dir)), name="covers")

location_icons_dir = Path(settings.location_icons_dir)
location_icons_dir.mkdir(parents=True, exist_ok=True)
app.mount("/location-icons", StaticFiles(directory=str(location_icons_dir)), name="location-icons")

platform_logos_dir = Path(settings.platform_logos_dir)
platform_logos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/platform-logos", StaticFiles(directory=str(platform_logos_dir)), name="platform-logos")


@app.get("/health", tags=["system"])
async def health():
    from .services.cache import lookup_cache
    return {"status": "ok", "version": "1.0.0", "cache_entries": lookup_cache.size()}
