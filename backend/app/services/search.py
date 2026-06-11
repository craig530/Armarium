import logging
import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger("armarium")

# Columns indexed for full-text search.
FTS_COLUMNS = ["title", "artist", "author", "director", "genres", "description"]

# Flipped to False if FTS5 isn't available (non-SQLite backend, or a SQLite
# build without the FTS5 extension). `list_media` falls back to per-column
# LIKE matching in that case.
FTS5_ENABLED = False

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


async def setup_fts(conn: AsyncConnection) -> None:
    """Create the `media_items_fts` external-content FTS5 table and the
    triggers that keep it in sync with `media_items`, then rebuild it if it's
    out of step (e.g. freshly added to a database that already has rows).

    Safe to run on every startup. Sets `FTS5_ENABLED` to False (without
    raising) if FTS5 isn't available.
    """
    global FTS5_ENABLED
    if conn.engine.dialect.name != "sqlite":
        FTS5_ENABLED = False
        return

    columns_sql = ", ".join(FTS_COLUMNS)
    new_values = ", ".join(f"new.{c}" for c in FTS_COLUMNS)
    old_values = ", ".join(f"old.{c}" for c in FTS_COLUMNS)

    existing = await conn.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='media_items_fts'")
    )
    table_existed = existing.first() is not None

    try:
        await conn.execute(text(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS media_items_fts USING fts5("
            f"{columns_sql}, content='media_items', content_rowid='id')"
        ))
        await conn.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS media_items_fts_ai AFTER INSERT ON media_items BEGIN
              INSERT INTO media_items_fts(rowid, {columns_sql}) VALUES (new.id, {new_values});
            END
        """))
        await conn.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS media_items_fts_ad AFTER DELETE ON media_items BEGIN
              INSERT INTO media_items_fts(media_items_fts, rowid, {columns_sql}) VALUES ('delete', old.id, {old_values});
            END
        """))
        await conn.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS media_items_fts_au AFTER UPDATE ON media_items BEGIN
              INSERT INTO media_items_fts(media_items_fts, rowid, {columns_sql}) VALUES ('delete', old.id, {old_values});
              INSERT INTO media_items_fts(rowid, {columns_sql}) VALUES (new.id, {new_values});
            END
        """))

        # The FTS index starts empty when the virtual table is first created
        # (CREATE VIRTUAL TABLE doesn't backfill it), so on the first run after
        # an upgrade — where `media_items` may already have rows — populate it
        # from the content table. On every subsequent startup the table
        # already exists and the triggers above have kept it in sync, so this
        # is skipped.
        if not table_existed:
            await conn.execute(text("INSERT INTO media_items_fts(media_items_fts) VALUES ('rebuild')"))
            logger.info("Built media_items_fts full-text index")
    except Exception:
        logger.warning("FTS5 unavailable — falling back to LIKE-based search", exc_info=True)
        FTS5_ENABLED = False
        return

    FTS5_ENABLED = True


def build_match_query(q: str) -> Optional[str]:
    """Turn a free-text search string into an FTS5 MATCH query that
    prefix-matches every word (so "lord ring" matches "Lord of the Rings").

    Returns None if `q` contains no word characters (e.g. only punctuation),
    in which case the caller should skip the FTS filter entirely — an empty
    MATCH query matches nothing rather than everything.

    Tokens are restricted to `\\w+` so none of FTS5's query-syntax characters
    (quotes, colons, parentheses, hyphens, etc.) ever reach the MATCH
    expression.
    """
    tokens = _TOKEN_RE.findall(q)
    if not tokens:
        return None
    return " AND ".join(f"{tok}*" for tok in tokens)
