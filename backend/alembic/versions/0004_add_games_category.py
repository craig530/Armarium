"""Add Games media category, developer/igdb_id columns, and default game subtypes

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, table, column as col, String, Integer

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default game subtypes seeded for new and upgraded installs.
# SQLAlchemy persists enum member *names*, not values.
_GAME_SUBTYPES = [
    {"name": "Nintendo Switch", "category": "GAMES", "supertype": "PHYSICAL", "sort_order": 0},
    {"name": "Xbox", "category": "GAMES", "supertype": "PHYSICAL", "sort_order": 1},
    {"name": "PlayStation", "category": "GAMES", "supertype": "PHYSICAL", "sort_order": 2},
    {"name": "Nintendo eShop", "category": "GAMES", "supertype": "DIGITAL", "sort_order": 0},
    {"name": "Microsoft Store", "category": "GAMES", "supertype": "DIGITAL", "sort_order": 1},
    {"name": "PlayStation Store", "category": "GAMES", "supertype": "DIGITAL", "sort_order": 2},
]

# Ad-hoc table definition for bulk_insert (no ORM import needed).
_media_subtypes = table(
    "media_subtypes",
    col("name", String(100)),
    col("category", String(20)),
    col("supertype", String(20)),
    col("sort_order", Integer),
)


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. Extend mediacategory enum ---
    # PostgreSQL: ALTER TYPE ... ADD VALUE is DDL; run it before any DML that
    # uses the new value.  SQLite stores enums as unconstrained VARCHAR, so
    # nothing to do there.
    if conn.dialect.name == "postgresql":
        conn.execute(text("ALTER TYPE mediacategory ADD VALUE IF NOT EXISTS 'GAMES'"))

    # --- 2. New columns on media_items ---
    with op.batch_alter_table("media_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("developer", sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column("igdb_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_media_items_igdb_id", ["igdb_id"], unique=False)

    # --- 3. Seed default game media subtypes (skip if already present) ---
    existing_names = {
        row[0]
        for row in conn.execute(
            text("SELECT name FROM media_subtypes WHERE category = 'GAMES'")
        ).fetchall()
    }
    rows_to_insert = [r for r in _GAME_SUBTYPES if r["name"] not in existing_names]
    if rows_to_insert:
        op.bulk_insert(_media_subtypes, rows_to_insert)


def downgrade() -> None:
    with op.batch_alter_table("media_items", schema=None) as batch_op:
        batch_op.drop_index("ix_media_items_igdb_id")
        batch_op.drop_column("igdb_id")
        batch_op.drop_column("developer")

    op.execute(text("DELETE FROM media_subtypes WHERE category = 'GAMES'"))

    # PostgreSQL: removing an enum value is not directly supported —
    # the type would need to be recreated, which risks breaking existing data.
    # On SQLite there is nothing to undo. Accept this as a limitation of
    # downgrading past this migration.
