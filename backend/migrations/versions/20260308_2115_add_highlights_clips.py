"""add clips column to highlights

Revision ID: a1b2c3d4e5f6
Revises: 7c624899f457
Create Date: 2026-03-08 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7c624899f457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('highlights', sa.Column('clips', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('highlights', 'clips')
