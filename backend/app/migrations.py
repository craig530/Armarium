import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

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
