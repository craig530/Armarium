import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from .database import Base

logger = logging.getLogger("armarium")


async def run_additive_migrations(conn: AsyncConnection) -> None:
    """Add model columns that are missing from already-existing tables.

    `Base.metadata.create_all()` only creates tables that don't exist yet —
    it never alters existing ones. Without this, a release that adds a new
    column would crash existing installs with "no such column" on first use.
    This covers the common case (new nullable columns) for SQLite; columns
    that aren't nullable, drops, renames and other backends still require a
    manual migration.
    """
    if conn.engine.dialect.name != "sqlite":
        return

    for table in Base.metadata.sorted_tables:
        result = await conn.execute(text(f'PRAGMA table_info("{table.name}")'))
        existing_columns = {row[1] for row in result.fetchall()}
        if not existing_columns:
            continue  # table doesn't exist yet — create_all will have made it

        for column in table.columns:
            if column.name in existing_columns:
                continue
            if not column.nullable:
                logger.warning(
                    "Column %s.%s is missing but not nullable — skipping "
                    "auto-migration; a manual migration is required.",
                    table.name, column.name,
                )
                continue

            ddl_type = column.type.compile(dialect=conn.dialect)
            await conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl_type}'))
            logger.info("Added missing column %s.%s", table.name, column.name)


# Default media subtypes seeded on first run. Each tuple is
# (name, category, supertype, sort_order).
def _default_media_subtypes():
    from .models.enums import MediaCategory, Supertype

    M, F, B = MediaCategory.MUSIC, MediaCategory.FILMS_TV, MediaCategory.BOOKS
    P, D = Supertype.PHYSICAL, Supertype.DIGITAL
    return [
        ("CD", M, P, 0),
        ("Digital Music", M, D, 0),
        ("Streaming Music", M, D, 1),
        ("DVD", F, P, 0),
        ("Blu-ray", F, P, 1),
        ("4K Blu-ray", F, P, 2),
        ("Digital Film", F, D, 0),
        ("Digital TV Series", F, D, 1),
        ("Streaming Film", F, D, 2),
        ("Streaming TV", F, D, 3),
        ("Book", B, P, 0),
        ("Graphic Novel", B, P, 1),
    ]


# Maps the legacy `media_items.media_type` enum values (stored as the
# uppercase enum *names*, e.g. "CD", "BLURAY") to the seeded subtype that
# replaces them.
_LEGACY_MEDIA_TYPE_TO_SUBTYPE = {
    "CD": "CD",
    "DVD": "DVD",
    "BLURAY": "Blu-ray",
    "BOOK": "Book",
}


async def seed_media_subtypes(session: AsyncSession) -> None:
    """Insert the default media subtypes if the table is empty."""
    from .models.media_subtype import MediaSubtype

    existing = (await session.execute(select(MediaSubtype.id).limit(1))).first()
    if existing is not None:
        return

    defaults = _default_media_subtypes()
    for name, category, supertype, sort_order in defaults:
        session.add(MediaSubtype(name=name, category=category, supertype=supertype, sort_order=sort_order))
    await session.commit()
    logger.info("Seeded %d default media subtypes", len(defaults))


async def backfill_media_subtypes(session: AsyncSession) -> None:
    """Point existing items' `media_subtype_id` at the subtype matching their
    legacy `media_type` value.

    `media_type` is no longer part of the ORM model, so it's read via raw SQL.
    Safe to run on every startup — only rows where `media_subtype_id IS NULL`
    are touched, so it's a no-op once applied.
    """
    from .models.media_subtype import MediaSubtype

    rows = (await session.execute(
        text("SELECT id, media_type FROM media_items WHERE media_subtype_id IS NULL")
    )).all()
    if not rows:
        return

    subtype_rows = (await session.execute(select(MediaSubtype.id, MediaSubtype.name))).all()
    subtype_id_by_name = {row.name: row.id for row in subtype_rows}

    updated = 0
    for row in rows:
        subtype_name = _LEGACY_MEDIA_TYPE_TO_SUBTYPE.get(row.media_type)
        subtype_id = subtype_id_by_name.get(subtype_name) if subtype_name else None
        if subtype_id is None:
            continue
        await session.execute(
            text("UPDATE media_items SET media_subtype_id = :sid WHERE id = :iid"),
            {"sid": subtype_id, "iid": row.id},
        )
        updated += 1

    if updated:
        await session.commit()
        logger.info("Backfilled media_subtype_id for %d item(s)", updated)
