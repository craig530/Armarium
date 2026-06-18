"""Add ownership: is_system on users, shared system user, app_config,
owner_id on media_items / item_lists / plex_library_mappings.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add is_system to users ───────────────────────────────────────────
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    # ── 2. Insert the "shared" system user ──────────────────────────────────
    # is_active=False prevents login via JWT auth; is_system=True hides it
    # from admin user lists. The hashed_password "!" can never be verified by
    # passlib/bcrypt so even a direct verify() call returns False.
    op.execute(
        sa.text(
            "INSERT INTO users "
            "(username, hashed_password, is_admin, is_active, is_read_only, "
            " can_add_items, can_manage_locations, can_manage_platforms, "
            " can_manage_media_types, can_manage_lists, can_manage_schedules, "
            " is_system) "
            "VALUES ('shared', '!', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)"
        )
    )

    # ── 3. Create app_config singleton table ────────────────────────────────
    op.create_table(
        "app_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ownership_mode", sa.String(length=20), nullable=False, server_default="shared"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(sa.text("INSERT INTO app_config (id, ownership_mode) VALUES (1, 'shared')"))

    # ── 4. Add owner_id to media_items ──────────────────────────────────────
    # Note: FK constraint is defined at the model layer; we omit the named
    # FK here to stay compatible with SQLite's batch_alter_table mode.
    with op.batch_alter_table("media_items") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_media_items_owner_id", ["owner_id"])

    op.execute(
        sa.text(
            "UPDATE media_items SET owner_id = "
            "(SELECT id FROM users WHERE username = 'shared' AND is_system = 1)"
        )
    )

    # ── 5. Add owner_id to item_lists (replace unique constraint too) ───────
    with op.batch_alter_table("item_lists") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_item_lists_owner_id", ["owner_id"])
        batch_op.drop_constraint("uq_item_lists_category_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_item_lists_category_owner_name", ["category", "owner_id", "name"]
        )

    op.execute(
        sa.text(
            "UPDATE item_lists SET owner_id = "
            "(SELECT id FROM users WHERE username = 'shared' AND is_system = 1)"
        )
    )

    # ── 6. Add owner_id to plex_library_mappings ────────────────────────────
    with op.batch_alter_table("plex_library_mappings") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_plex_library_mappings_owner_id", ["owner_id"])

    op.execute(
        sa.text(
            "UPDATE plex_library_mappings SET owner_id = "
            "(SELECT id FROM users WHERE username = 'shared' AND is_system = 1)"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("plex_library_mappings") as batch_op:
        batch_op.drop_index("ix_plex_library_mappings_owner_id")
        batch_op.drop_column("owner_id")

    with op.batch_alter_table("item_lists") as batch_op:
        batch_op.drop_constraint("uq_item_lists_category_owner_name", type_="unique")
        batch_op.create_unique_constraint("uq_item_lists_category_name", ["category", "name"])
        batch_op.drop_index("ix_item_lists_owner_id")
        batch_op.drop_column("owner_id")

    with op.batch_alter_table("media_items") as batch_op:
        batch_op.drop_index("ix_media_items_owner_id")
        batch_op.drop_column("owner_id")

    op.drop_table("app_config")

    op.execute(sa.text("DELETE FROM users WHERE username = 'shared' AND is_system = 1"))

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_system")
