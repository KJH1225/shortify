"""Initial schema - videos and highlights tables

Revision ID: 001
Revises:
Create Date: 2026-02-08 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('source_url', sa.String(512), nullable=True),
        sa.Column('source_filename', sa.String(255), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('idle', 'uploading', 'processing', 'completed', 'error', name='processingstatus'), nullable=False),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('message', sa.Text(), default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_videos_status', 'videos', ['status'])
    op.create_index('ix_videos_created_at', 'videos', ['created_at'])

    # Create highlights table
    op.create_table(
        'highlights',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('video_id', sa.String(36), sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('thumbnail_url', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_highlights_video_id', 'highlights', ['video_id'])
    op.create_index('ix_highlights_score', 'highlights', ['score'])


def downgrade() -> None:
    op.drop_index('ix_highlights_score', 'highlights')
    op.drop_index('ix_highlights_video_id', 'highlights')
    op.drop_table('highlights')

    op.drop_index('ix_videos_created_at', 'videos')
    op.drop_index('ix_videos_status', 'videos')
    op.drop_table('videos')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS processingstatus')
