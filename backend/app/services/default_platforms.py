import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.platform import Platform

logger = logging.getLogger("armarium")

# logo_key values must match an entry in frontend/src/lib/platformLogos.js's
# PLATFORM_LOGOS registry. Kept in sync with
# alembic/versions/0011_update_games_subtypes.py, which applies this list to
# fresh databases. This copy backs reset_database's reseed of an
# already-migrated database.
DEFAULT_PLATFORMS = [
    ("Plex", "plex"),
    ("Audible", "audible"),
    ("Kindle", "kindle"),
    ("PlayStation Store", "playstation"),
    ("Microsoft Store", "microsoftstore"),
    ("Nintendo eShop", "nintendoeshop"),
    ("Apple TV", "appletv"),
    ("Amazon Music", "amazon_music"),
]


async def seed_default_platforms(session: AsyncSession) -> None:
    """Insert the default platforms if the table is empty."""
    existing = (await session.execute(select(Platform.id).limit(1))).first()
    if existing is not None:
        return

    for name, logo_key in DEFAULT_PLATFORMS:
        session.add(Platform(name=name, logo_key=logo_key))
    await session.commit()
    logger.info("Seeded %d default platforms", len(DEFAULT_PLATFORMS))
