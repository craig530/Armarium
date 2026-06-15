"""add item_lists, media_item_lists association table, and can_manage_lists permission

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'item_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        # create_type=False — the `mediacategory` Postgres enum type is already
        # created by the media_subtypes table in 0001_baseline.
        sa.Column('category', sa.Enum('MUSIC', 'FILMS_TV', 'BOOKS', name='mediacategory', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', 'name', name='uq_item_lists_category_name'),
    )
    with op.batch_alter_table('item_lists', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_item_lists_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_item_lists_id'), ['id'], unique=False)

    op.create_table(
        'media_item_lists',
        sa.Column('media_item_id', sa.Integer(), nullable=False),
        sa.Column('item_list_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['media_item_id'], ['media_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_list_id'], ['item_lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('media_item_id', 'item_list_id'),
    )
    with op.batch_alter_table('media_item_lists', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_media_item_lists_item_list_id'), ['item_list_id'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('can_manage_lists', sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('can_manage_lists')

    with op.batch_alter_table('media_item_lists', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_media_item_lists_item_list_id'))
    op.drop_table('media_item_lists')

    with op.batch_alter_table('item_lists', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_item_lists_id'))
        batch_op.drop_index(batch_op.f('ix_item_lists_category'))
    op.drop_table('item_lists')
