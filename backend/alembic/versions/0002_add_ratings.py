"""add tmdb_rating and user_rating columns to media_items

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tmdb_rating', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('user_rating', sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            'ck_media_items_user_rating_range',
            'user_rating IS NULL OR (user_rating BETWEEN 1 AND 5)',
        )


def downgrade() -> None:
    with op.batch_alter_table('media_items', schema=None) as batch_op:
        batch_op.drop_constraint('ck_media_items_user_rating_range', type_='check')
        batch_op.drop_column('user_rating')
        batch_op.drop_column('tmdb_rating')
