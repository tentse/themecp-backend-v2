"""add_user_contest_stats_columns

Revision ID: c9e4d73f1a2b
Revises: 364a31033a35
Create Date: 2026-02-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9e4d73f1a2b"
down_revision: Union[str, Sequence[str], None] = "364a31033a35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("contest_rating", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("max_contest_rating", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("best_performance", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "contest_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "contest_attempts")
    op.drop_column("users", "best_performance")
    op.drop_column("users", "max_contest_rating")
    op.drop_column("users", "contest_rating")
