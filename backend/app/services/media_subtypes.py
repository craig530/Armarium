import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.enums import MediaCategory, Supertype
from ..models.media_subtype import MediaSubtype

logger = logging.getLogger("armarium")

# Kept in sync with alembic/versions/0001_baseline.py (Music/Films & TV/
# Books) and 0011_update_games_subtypes.py (Games), which apply this list to
# fresh/existing databases respectively. This copy backs reset_database's
# reseed of an already-migrated database.
M, F, B, G = MediaCategory.MUSIC, MediaCategory.FILMS_TV, MediaCategory.BOOKS, MediaCategory.GAMES
P, D = Supertype.PHYSICAL, Supertype.DIGITAL
DEFAULT_MEDIA_SUBTYPES = [
    ("CD", M, P, 0),
    ("Music", M, D, 0),
    ("DVD", F, P, 0),
    ("Blu-ray", F, P, 1),
    ("Film", F, D, 0),
    ("TV Series", F, D, 1),
    ("Book", B, P, 0),
    ("Graphic Novel", B, P, 1),
    ("eBook", B, D, 0),
    ("Audiobook", B, D, 1),
    ("Disc", G, P, 0),
    ("Cartridge", G, P, 1),
    ("Game", G, D, 0),
]


async def seed_default_media_subtypes(session: AsyncSession) -> None:
    """Insert the default media subtypes if the table is empty."""
    existing = (await session.execute(select(MediaSubtype.id).limit(1))).first()
    if existing is not None:
        return

    for name, category, supertype, sort_order in DEFAULT_MEDIA_SUBTYPES:
        session.add(MediaSubtype(name=name, category=category, supertype=supertype, sort_order=sort_order))
    await session.commit()
    logger.info("Seeded %d default media subtypes", len(DEFAULT_MEDIA_SUBTYPES))
