"""add ends_at to contest_session

Revision ID: d1e5f84a2c3d
Revises: c9e4d73f1a2b
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e5f84a2c3d"
down_revision: Union[str, Sequence[str], None] = "c9e4d73f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ends_at column to contest_session table."""
    op.add_column(
        "contest_session",
        sa.Column("ends_at", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    """Remove ends_at column from contest_session table."""
    op.drop_column("contest_session", "ends_at")
