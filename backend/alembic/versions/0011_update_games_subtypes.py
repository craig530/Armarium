"""Replace default Games media subtypes; seed default platforms/locations.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_GAME_SUBTYPE_NAMES = {
    "Nintendo Switch", "Xbox", "PlayStation",
    "Nintendo eShop", "Microsoft Store", "PlayStation Store",
}

_NEW_GAME_SUBTYPES = [
    {"name": "Disc", "category": "GAMES", "supertype": "PHYSICAL", "sort_order": 0},
    {"name": "Cartridge", "category": "GAMES", "supertype": "PHYSICAL", "sort_order": 1},
    {"name": "Game", "category": "GAMES", "supertype": "DIGITAL", "sort_order": 0},
]

_DEFAULT_PLATFORMS = [
    {"name": "Plex", "logo_key": "plex"},
    {"name": "Audible", "logo_key": "audible"},
    {"name": "Kindle", "logo_key": "kindle"},
    {"name": "PlayStation Store", "logo_key": "playstation"},
    {"name": "Microsoft Store", "logo_key": "microsoftstore"},
    {"name": "Nintendo eShop", "logo_key": "nintendoeshop"},
    {"name": "Apple TV", "logo_key": "appletv"},
    {"name": "Amazon Music", "logo_key": "amazon_music"},
]

_DEFAULT_LOCATIONS = [
    {"name": "Living Room", "icon_key": "living_room", "sort_order": 0},
    {"name": "Master Bedroom", "icon_key": "bedroom", "sort_order": 1},
    {"name": "Office", "icon_key": "office", "sort_order": 2},
]

# Ad-hoc tables for bulk_insert. media_subtypes' category/supertype must use
# sa.Enum with create_type=False (types already exist) so SQLAlchemy wraps
# the bound parameters in CAST(... AS mediacategory/supertype) — plain
# String columns cause a DatatypeMismatchError with asyncpg on PostgreSQL.
_media_subtypes = sa.table(
    "media_subtypes",
    sa.column("name", sa.String(100)),
    sa.column("category", sa.Enum(
        "MUSIC", "FILMS_TV", "BOOKS", "GAMES",
        name="mediacategory", create_type=False,
    )),
    sa.column("supertype", sa.Enum(
        "PHYSICAL", "DIGITAL",
        name="supertype", create_type=False,
    )),
    sa.column("sort_order", sa.Integer),
)
_platforms = sa.table(
    "platforms",
    sa.column("name", sa.String(200)),
    sa.column("logo_key", sa.String(100)),
)
_locations = sa.table(
    "locations",
    sa.column("name", sa.String(200)),
    sa.column("icon_key", sa.String(50)),
    sa.column("sort_order", sa.Integer),
)


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. Replace the default Games subtypes ---
    # Only delete an old subtype if nothing references it (ON DELETE
    # RESTRICT on media_items.media_subtype_id and
    # plex_library_mappings.media_subtype_id) — an admin's existing game
    # items keep their current subtype rather than losing it.
    rows = conn.execute(text("SELECT id, name FROM media_subtypes WHERE category = 'GAMES'")).fetchall()
    for subtype_id, name in rows:
        if name not in _OLD_GAME_SUBTYPE_NAMES:
            continue
        media_in_use = conn.execute(
            text("SELECT COUNT(*) FROM media_items WHERE media_subtype_id = :id"), {"id": subtype_id}
        ).scalar()
        plex_in_use = conn.execute(
            text("SELECT COUNT(*) FROM plex_library_mappings WHERE media_subtype_id = :id"), {"id": subtype_id}
        ).scalar()
        if media_in_use == 0 and plex_in_use == 0:
            conn.execute(text("DELETE FROM media_subtypes WHERE id = :id"), {"id": subtype_id})

    existing_names = {
        row[0] for row in conn.execute(text("SELECT name FROM media_subtypes WHERE category = 'GAMES'")).fetchall()
    }
    rows_to_insert = [r for r in _NEW_GAME_SUBTYPES if r["name"] not in existing_names]
    if rows_to_insert:
        op.bulk_insert(_media_subtypes, rows_to_insert)

    # --- 2. Seed default platforms/locations, but only into an empty table
    # --- (an admin's existing custom platforms/locations are left alone).
    if conn.execute(text("SELECT 1 FROM platforms LIMIT 1")).first() is None:
        op.bulk_insert(_platforms, _DEFAULT_PLATFORMS)

    if conn.execute(text("SELECT 1 FROM locations LIMIT 1")).first() is None:
        op.bulk_insert(_locations, _DEFAULT_LOCATIONS)


def downgrade() -> None:
    # Not reversible: there's no way to tell which platforms/locations (if
    # any) were seeded by this migration vs. created by the admin
    # afterward, and the old Games subtypes deleted above can't be
    # recreated with their original ids. Accept this as a limitation, same
    # as 0004_add_games_category.py's enum-value downgrade.
    pass
