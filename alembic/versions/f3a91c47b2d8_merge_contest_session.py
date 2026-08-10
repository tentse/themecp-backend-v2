"""merge problem statuses and result into contest_session

Folds contest_session_problems_status (exactly 4 rows per session) and
contest_session_result (exactly 1 row per session) into contest_session.

Both children had a fixed cardinality, so they can be columns. That removes the
per-row lookups the contest history was doing: at limit=50 the endpoint issued
103 sequential queries, and over a remote database the cost is dominated by
round trips rather than by Postgres.

Also restores the contest_session_seen_problem primary key, which was dropped as
collateral damage by a81e39f8ee47 (dropping a column that participates in a
composite primary key drops the whole constraint), and recreates the session
indexes that 1ff5fb2df58b removed.

Revision ID: f3a91c47b2d8
Revises: 1ff5fb2df58b
Create Date: 2026-08-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a91c47b2d8'
down_revision: Union[str, Sequence[str], None] = '1ff5fb2df58b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROBLEM_NUMBERS = (1, 2, 3, 4)
OUTCOME_COLUMNS = ('performance', 'rating_before', 'rating_after', 'rating_delta')


def upgrade() -> None:
    """Upgrade schema."""
    # 1. New columns are all nullable: they used to live in tables whose rows did
    #    not exist until RUNNING (statuses) or FINISHED (outcome), while the
    #    merged row exists from REVIEW onward.
    for problem_number in PROBLEM_NUMBERS:
        op.add_column('contest_session', sa.Column(f'p{problem_number}_rating', sa.Integer(), nullable=True))
        op.add_column('contest_session', sa.Column(f'p{problem_number}_status', sa.String(length=255), nullable=True))
        op.add_column('contest_session', sa.Column(f'p{problem_number}_accepted_at', sa.BigInteger(), nullable=True))
        op.add_column('contest_session', sa.Column(f'p{problem_number}_solved_in_min', sa.Integer(), nullable=True))

    for column_name in OUTCOME_COLUMNS:
        op.add_column('contest_session', sa.Column(column_name, sa.Integer(), nullable=True))

    # 2. Pivot the four status rows into four column sets, one UPDATE per slot.
    #    accepted_at was String(255) holding a unix timestamp; the cast is safe
    #    because str(submission_time) was the only writer and it was always read
    #    back through int().
    for problem_number in PROBLEM_NUMBERS:
        op.execute(f"""
            UPDATE contest_session AS cs SET
                p{problem_number}_rating = s.problem_rating,
                p{problem_number}_status = s.status,
                p{problem_number}_accepted_at = NULLIF(s.accepted_at, '')::bigint,
                p{problem_number}_solved_in_min = s.solved_in_min
            FROM contest_session_problems_status AS s
            WHERE s.session_id = cs.id AND s.problem_number = {problem_number}
        """)

    # 3. Backfill the outcome. solved_count is deliberately not carried over: it
    #    was written on every contest end and never read anywhere.
    op.execute("""
        UPDATE contest_session AS cs SET
            performance = r.performance,
            rating_before = r.rating_before,
            rating_after = r.rating_after,
            rating_delta = r.rating_delta
        FROM contest_session_result AS r
        WHERE r.session_id = cs.id
    """)

    # 4. Restore the seen-problem primary key. Guarded because the constraint may
    #    still be present on databases that never ran the migration that dropped
    #    it. Exact duplicate rows are removed first: without the key nothing
    #    prevented them, and identical rows carry no information.
    op.execute("""
        DELETE FROM contest_session_seen_problem a
        USING contest_session_seen_problem b
        WHERE a.ctid > b.ctid
          AND a.session_id = b.session_id
          AND a."cf_problem_contestID" = b."cf_problem_contestID"
          AND a.cf_problem_index = b.cf_problem_index
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'contest_session_seen_problem'::regclass
                  AND contype = 'p'
            ) THEN
                ALTER TABLE contest_session_seen_problem
                    ADD CONSTRAINT contest_session_seen_problem_pkey
                    PRIMARY KEY (session_id, "cf_problem_contestID", cf_problem_index);
            END IF;
        END $$;
    """)

    # 5. Indexes. These are also declared on the model, so that a future
    #    `alembic revision --autogenerate` does not read them as drift and drop
    #    them again, which is exactly what happened in 1ff5fb2df58b.
    op.create_index(
        'ix_contest_session_user_id_status',
        'contest_session',
        ['user_id', 'status']
    )
    op.execute("""
        CREATE INDEX ix_contest_session_user_id_status_starts_at
            ON contest_session (user_id, status, starts_at DESC NULLS LAST)
    """)

    # 6. The children are now redundant.
    op.drop_table('contest_session_problems_status')
    op.drop_table('contest_session_result')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'contest_session_problems_status',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('problem_number', sa.Integer(), nullable=False),
        sa.Column('problem_contestID', sa.String(length=255), nullable=False),
        sa.Column('problem_index', sa.String(length=255), nullable=False),
        sa.Column('problem_rating', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.Column('accepted_at', sa.String(length=255), nullable=True),
        sa.Column('solved_in_min', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['contest_session.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'contest_session_result',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('solved_count', sa.Integer(), nullable=False),
        sa.Column('performance', sa.Integer(), nullable=False),
        sa.Column('rating_before', sa.Integer(), nullable=False),
        sa.Column('rating_after', sa.Integer(), nullable=False),
        sa.Column('rating_delta', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['contest_session.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Reverse pivot. Only sessions that reached RUNNING have statuses, and the
    # problem identity comes from the session's own columns, which is where the
    # child table's duplicated copy came from in the first place.
    for problem_number in PROBLEM_NUMBERS:
        op.execute(f"""
            INSERT INTO contest_session_problems_status
                (session_id, problem_number, "problem_contestID", problem_index,
                 problem_rating, status, accepted_at, solved_in_min)
            SELECT
                id,
                {problem_number},
                "p{problem_number}_cf_contestID",
                p{problem_number}_cf_index,
                p{problem_number}_rating,
                p{problem_number}_status,
                p{problem_number}_accepted_at::text,
                p{problem_number}_solved_in_min
            FROM contest_session
            WHERE p{problem_number}_status IS NOT NULL
              AND p{problem_number}_rating IS NOT NULL
        """)

    # solved_count was dropped, so recompute it from the statuses.
    # Ordered by start time so the regenerated ids run chronologically, which is
    # what the old `ORDER BY contest_session_result.id` relied on.
    solved_count_expression = " + ".join(
        f"(CASE WHEN p{problem_number}_status = 'SOLVED' THEN 1 ELSE 0 END)"
        for problem_number in PROBLEM_NUMBERS
    )
    op.execute(f"""
        INSERT INTO contest_session_result
            (session_id, solved_count, performance, rating_before, rating_after, rating_delta)
        SELECT
            id,
            {solved_count_expression},
            performance,
            rating_before,
            rating_after,
            rating_delta
        FROM contest_session
        WHERE performance IS NOT NULL
        ORDER BY starts_at ASC NULLS FIRST, id ASC
    """)

    op.execute("DROP INDEX IF EXISTS ix_contest_session_user_id_status_starts_at")
    op.drop_index('ix_contest_session_user_id_status', table_name='contest_session')

    for column_name in OUTCOME_COLUMNS:
        op.drop_column('contest_session', column_name)

    for problem_number in PROBLEM_NUMBERS:
        op.drop_column('contest_session', f'p{problem_number}_solved_in_min')
        op.drop_column('contest_session', f'p{problem_number}_accepted_at')
        op.drop_column('contest_session', f'p{problem_number}_status')
        op.drop_column('contest_session', f'p{problem_number}_rating')

    # The seen-problem primary key is intentionally left in place: it repairs
    # unintended drift rather than implementing this revision, and the upgrade
    # path adds it only when missing.
