"""Add disabled_categories to app_config.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_config") as batch_op:
        batch_op.add_column(
            sa.Column(
                "disabled_categories",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
    # SQLite batch mode may store the server_default as a literal string rather
    # than evaluating the SQL expression, so explicitly set the correct value.
    op.execute(sa.text("UPDATE app_config SET disabled_categories = '[]'"))


def downgrade() -> None:
    with op.batch_alter_table("app_config") as batch_op:
        batch_op.drop_column("disabled_categories")
