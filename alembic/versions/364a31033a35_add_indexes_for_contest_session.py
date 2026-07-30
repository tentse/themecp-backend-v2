"""add_indexes_for_contest_session

Revision ID: 364a31033a35
Revises: 80717235d0d5
Create Date: 2026-02-16 09:54:09.269920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '364a31033a35'
down_revision: Union[str, Sequence[str], None] = '80717235d0d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add index on contest_session.user_id for faster user lookups
    op.create_index(
        'ix_contest_session_user_id',
        'contest_session',
        ['user_id'],
        unique=False
    )
    
    # Add index on contest_session.status for filtering by status
    op.create_index(
        'ix_contest_session_status',
        'contest_session',
        ['status'],
        unique=False
    )
    
    # Add composite index on (user_id, status) for common query pattern
    op.create_index(
        'ix_contest_session_user_id_status',
        'contest_session',
        ['user_id', 'status'],
        unique=False
    )
    
    # Add index on contest_session_problems_status.session_id (foreign key)
    op.create_index(
        'ix_contest_session_problems_status_session_id',
        'contest_session_problems_status',
        ['session_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_contest_session_problems_status_session_id', table_name='contest_session_problems_status')
    op.drop_index('ix_contest_session_user_id_status', table_name='contest_session')
    op.drop_index('ix_contest_session_status', table_name='contest_session')
    op.drop_index('ix_contest_session_user_id', table_name='contest_session')
