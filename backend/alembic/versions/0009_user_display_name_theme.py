"""Add display_name and theme_preference to users.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "theme_preference",
                sa.String(10),
                nullable=False,
                server_default="auto",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("theme_preference")
        batch_op.drop_column("display_name")
