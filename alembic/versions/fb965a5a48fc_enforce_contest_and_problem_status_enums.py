"""enforce contest and problem status enums

Replace the five VARCHAR status columns with two shared PostgreSQL enum types.
Keep problem statuses nullable for sessions in REVIEW. Explicit casts reject
invalid existing strings rather than silently changing contest history.

Revision ID: fb965a5a48fc
Revises: f3a91c47b2d8
Create Date: 2026-10-02 11:34:33.064587

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fb965a5a48fc'
down_revision: Union[str, Sequence[str], None] = 'f3a91c47b2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Freeze the labels here: old migrations must not depend on future changes to
# the application's Python enums.
CONTEST_STATUS_ENUM = postgresql.ENUM(
    'REVIEW', 'RUNNING', 'FINISHED', name='contest_status'
)
PROBLEM_STATUS_ENUM = postgresql.ENUM(
    'UNSOLVED', 'SOLVED', 'UPSOLVED', name='problem_status'
)


def upgrade() -> None:
    """Create the enum types and convert existing status values in place."""
    bind = op.get_bind()
    CONTEST_STATUS_ENUM.create(bind, checkfirst=False)
    PROBLEM_STATUS_ENUM.create(bind, checkfirst=False)

    # Convert all five columns in one ALTER TABLE so PostgreSQL can share the
    # table rewrite. Nullability, indexes, and stored results are preserved.
    op.execute("""
        ALTER TABLE contest_session
            ALTER COLUMN status TYPE contest_status
                USING status::contest_status,
            ALTER COLUMN p1_status TYPE problem_status
                USING p1_status::problem_status,
            ALTER COLUMN p2_status TYPE problem_status
                USING p2_status::problem_status,
            ALTER COLUMN p3_status TYPE problem_status
                USING p3_status::problem_status,
            ALTER COLUMN p4_status TYPE problem_status
                USING p4_status::problem_status
    """)


def downgrade() -> None:
    """Restore VARCHAR columns before dropping their shared enum types."""
    op.execute("""
        ALTER TABLE contest_session
            ALTER COLUMN status TYPE VARCHAR(255)
                USING status::text,
            ALTER COLUMN p1_status TYPE VARCHAR(255)
                USING p1_status::text,
            ALTER COLUMN p2_status TYPE VARCHAR(255)
                USING p2_status::text,
            ALTER COLUMN p3_status TYPE VARCHAR(255)
                USING p3_status::text,
            ALTER COLUMN p4_status TYPE VARCHAR(255)
                USING p4_status::text
    """)

    bind = op.get_bind()
    PROBLEM_STATUS_ENUM.drop(bind, checkfirst=False)
    CONTEST_STATUS_ENUM.drop(bind, checkfirst=False)
