"""rename state to status in contest_session_problems_status

Revision ID: e2f6a95b3d4e
Revises: d1e5f84a2c3d
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f6a95b3d4e"
down_revision: Union[str, Sequence[str], None] = "d1e5f84a2c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename state column to status in contest_session_problems_status."""
    op.alter_column(
        "contest_session_problems_status",
        "state",
        new_column_name="status",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    """Rename status column back to state."""
    op.alter_column(
        "contest_session_problems_status",
        "status",
        new_column_name="state",
        existing_type=sa.String(length=255),
        nullable=False,
    )
