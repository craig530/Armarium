"""Add plex_rating_key to media_items and machine_identifier to plex_config

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media_items") as batch_op:
        batch_op.add_column(sa.Column("plex_rating_key", sa.String(50), nullable=True))
        batch_op.create_index("ix_media_items_plex_rating_key", ["plex_rating_key"])

    with op.batch_alter_table("plex_config") as batch_op:
        batch_op.add_column(sa.Column("machine_identifier", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("plex_config") as batch_op:
        batch_op.drop_column("machine_identifier")

    with op.batch_alter_table("media_items") as batch_op:
        batch_op.drop_index("ix_media_items_plex_rating_key")
        batch_op.drop_column("plex_rating_key")
