import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.location import Location

logger = logging.getLogger("armarium")

# icon_key values must match an entry in frontend/src/lib/locationIcons.js's
# LOCATION_ICONS registry. Kept in sync with
# alembic/versions/0011_update_games_subtypes.py, which applies this list to
# fresh databases. This copy backs reset_database's reseed of an
# already-migrated database.
DEFAULT_LOCATIONS = [
    ("Living Room", "living_room", 0),
    ("Master Bedroom", "bedroom", 1),
    ("Office", "office", 2),
]


async def seed_default_locations(session: AsyncSession) -> None:
    """Insert the default locations if the table is empty."""
    existing = (await session.execute(select(Location.id).limit(1))).first()
    if existing is not None:
        return

    for name, icon_key, sort_order in DEFAULT_LOCATIONS:
        session.add(Location(name=name, icon_key=icon_key, sort_order=sort_order))
    await session.commit()
    logger.info("Seeded %d default locations", len(DEFAULT_LOCATIONS))
