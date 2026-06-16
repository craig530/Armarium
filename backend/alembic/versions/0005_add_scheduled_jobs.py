"""add scheduled jobs, sync result columns, and can_manage_schedules

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("interval_hours", sa.Integer(), nullable=False),
        sa.Column("auto_remove_stale", sa.Boolean(), nullable=True),
        sa.Column("export_base_dir", sa.String(length=500), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_status", sa.String(length=20), nullable=True),
        sa.Column("last_run_created", sa.Integer(), nullable=True),
        sa.Column("last_run_updated", sa.Integer(), nullable=True),
        sa.Column("last_run_removed", sa.Integer(), nullable=True),
        sa.Column("last_run_error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_jobs_job_type", "scheduled_jobs", ["job_type"])
    op.create_index("ix_scheduled_jobs_target_id", "scheduled_jobs", ["target_id"])

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "can_manage_schedules",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            )
        )

    with op.batch_alter_table("plex_library_mappings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("last_sync_status", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("last_sync_created", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_sync_updated", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_sync_removed", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_sync_error", sa.String(length=1000), nullable=True))


def downgrade():
    with op.batch_alter_table("plex_library_mappings", schema=None) as batch_op:
        batch_op.drop_column("last_sync_error")
        batch_op.drop_column("last_sync_removed")
        batch_op.drop_column("last_sync_updated")
        batch_op.drop_column("last_sync_created")
        batch_op.drop_column("last_sync_status")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("can_manage_schedules")

    op.drop_index("ix_scheduled_jobs_target_id", table_name="scheduled_jobs")
    op.drop_index("ix_scheduled_jobs_job_type", table_name="scheduled_jobs")
    op.drop_table("scheduled_jobs")
