"""
Tests for the contest_session merge migration (f3a91c47b2d8).

Merging the two child tables into contest_session is the only irreversible step
in the refactor, so the backfill is verified directly: insert rows in the old
shape at the previous revision, upgrade, and check the data landed on the right
columns.

Runs against its own database. The rest of the suite migrates once per session
and isolates tests by rolling back a transaction, which a test that drives
migrations would fight.
"""
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

MIGRATION_DB_NAME = "themecp_v2_migration_test"
ADMIN_DB_URL = "postgresql://themecp_test:themecp_test@localhost:5433/themecp_v2_test"
MIGRATION_DB_URL = f"postgresql://themecp_test:themecp_test@localhost:5433/{MIGRATION_DB_NAME}"

BEFORE_MERGE = "1ff5fb2df58b"
AFTER_MERGE = "f3a91c47b2d8"

SESSION_ID = "finished-session"
REVIEW_SESSION_ID = "review-session"


def _run_admin_statement(statement: str) -> None:
    """CREATE/DROP DATABASE cannot run inside a transaction."""
    admin_engine = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(statement))
    finally:
        admin_engine.dispose()


def _drop_migration_database() -> None:
    """
    Alembic builds its own engine inside env.py and never disposes it, so a
    connection outlives the command and would block the drop.
    """
    _run_admin_statement(f"""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{MIGRATION_DB_NAME}' AND pid <> pg_backend_pid()
    """)
    _run_admin_statement(f'DROP DATABASE IF EXISTS "{MIGRATION_DB_NAME}"')


@pytest.fixture
def migration_engine(docker_compose, monkeypatch):
    """
    A dedicated, empty database plus alembic pointed at it.

    Depends on docker_compose because that fixture owns the container lifecycle
    and stops it at session teardown; without it this module cannot run alone.
    """
    _drop_migration_database()
    _run_admin_statement(f'CREATE DATABASE "{MIGRATION_DB_NAME}"')

    # env.py reads this and overrides whatever the caller sets on the config,
    # so it is the only thing that actually redirects the migration.
    monkeypatch.setenv("PG_DATABASE_URL", MIGRATION_DB_URL)

    engine = create_engine(MIGRATION_DB_URL)
    try:
        yield engine
    finally:
        engine.dispose()
        _drop_migration_database()


@pytest.fixture
def alembic_config():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config = Config(os.path.join(project_root, "alembic.ini"))
    config.set_main_option("sqlalchemy.url", MIGRATION_DB_URL)
    return config


def _insert_old_shape_rows(engine) -> None:
    """Insert a finished session and a review session in the pre-merge shape."""
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO contest_session
                (id, user_id, level, theme, duration_in_min, status, starts_at, ends_at,
                 "p1_cf_contestID", p1_cf_index, "p2_cf_contestID", p2_cf_index,
                 "p3_cf_contestID", p3_cf_index, "p4_cf_contestID", p4_cf_index)
            VALUES
                (:sid, 'user-1', 21, 'greedy', 120, 'FINISHED', 1700000000, 1700007200,
                 '111', 'A', '222', 'B', '333', 'C', '444', 'D'),
                (:rid, 'user-1', 21, 'greedy', 120, 'REVIEW', NULL, NULL,
                 '555', 'A', '666', 'B', '777', 'C', '888', 'D')
        """), {"sid": SESSION_ID, "rid": REVIEW_SESSION_ID})

        # accepted_at was a VARCHAR holding a unix timestamp
        connection.execute(text("""
            INSERT INTO contest_session_problems_status
                (session_id, problem_number, "problem_contestID", problem_index,
                 problem_rating, status, accepted_at, solved_in_min)
            VALUES
                (:sid, 1, '111', 'A', 1100, 'SOLVED',   '1700000300', 5),
                (:sid, 2, '222', 'B', 1200, 'SOLVED',   '1700001200', 20),
                (:sid, 3, '333', 'C', 1300, 'UNSOLVED', NULL, NULL),
                (:sid, 4, '444', 'D', 1400, 'UNSOLVED', NULL, NULL)
        """), {"sid": SESSION_ID})

        connection.execute(text("""
            INSERT INTO contest_session_result
                (session_id, solved_count, performance, rating_before, rating_after, rating_delta)
            VALUES (:sid, 2, 1650, 1400, 1417, 17)
        """), {"sid": SESSION_ID})

        # Two identical seen rows: nothing prevented them once the primary key
        # was lost, and the migration has to cope before restoring it.
        connection.execute(text("""
            INSERT INTO contest_session_seen_problem
                (session_id, "cf_problem_contestID", cf_problem_index)
            VALUES (:sid, '111', 'A'), (:sid, '111', 'A'), (:sid, '222', 'B')
        """), {"sid": SESSION_ID})


class TestMergeMigration:

    def test_backfills_problem_slots_and_outcome(self, migration_engine, alembic_config):
        """Old child-table rows land on the right columns of the merged row."""
        command.upgrade(alembic_config, BEFORE_MERGE)
        _insert_old_shape_rows(migration_engine)
        command.upgrade(alembic_config, AFTER_MERGE)

        with migration_engine.connect() as connection:
            row = connection.execute(text("""
                SELECT p1_rating, p1_status, p1_accepted_at, p1_solved_in_min,
                       p2_rating, p2_status, p2_accepted_at, p2_solved_in_min,
                       p3_status, p3_accepted_at, p3_solved_in_min,
                       performance, rating_before, rating_after, rating_delta
                FROM contest_session WHERE id = :sid
            """), {"sid": SESSION_ID}).one()

        assert row.p1_rating == 1100
        assert row.p1_status == "SOLVED"
        assert row.p1_solved_in_min == 5
        assert row.p2_rating == 1200
        assert row.p2_status == "SOLVED"
        assert row.p2_solved_in_min == 20
        assert row.p3_status == "UNSOLVED"
        assert row.p3_accepted_at is None
        assert row.p3_solved_in_min is None

        assert row.performance == 1650
        assert row.rating_before == 1400
        assert row.rating_after == 1417
        assert row.rating_delta == 17

    def test_accepted_at_becomes_an_integer(self, migration_engine, alembic_config):
        """The VARCHAR timestamp is carried over as a real BIGINT."""
        command.upgrade(alembic_config, BEFORE_MERGE)
        _insert_old_shape_rows(migration_engine)
        command.upgrade(alembic_config, AFTER_MERGE)

        with migration_engine.connect() as connection:
            accepted_at = connection.execute(text(
                "SELECT p1_accepted_at FROM contest_session WHERE id = :sid"
            ), {"sid": SESSION_ID}).scalar_one()

            data_type = connection.execute(text("""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = 'contest_session' AND column_name = 'p1_accepted_at'
            """)).scalar_one()

        assert accepted_at == 1700000300
        assert isinstance(accepted_at, int)
        assert data_type == "bigint"

    def test_session_that_never_started_keeps_null_slots(self, migration_engine, alembic_config):
        """
        A REVIEW session had no child rows at all, which is exactly why the new
        columns have to be nullable.
        """
        command.upgrade(alembic_config, BEFORE_MERGE)
        _insert_old_shape_rows(migration_engine)
        command.upgrade(alembic_config, AFTER_MERGE)

        with migration_engine.connect() as connection:
            row = connection.execute(text("""
                SELECT p1_rating, p1_status, p1_accepted_at, p1_solved_in_min, performance
                FROM contest_session WHERE id = :rid
            """), {"rid": REVIEW_SESSION_ID}).one()

        assert row.p1_rating is None
        assert row.p1_status is None
        assert row.p1_accepted_at is None
        assert row.p1_solved_in_min is None
        assert row.performance is None

    def test_child_tables_are_dropped(self, migration_engine, alembic_config):
        command.upgrade(alembic_config, BEFORE_MERGE)
        _insert_old_shape_rows(migration_engine)
        command.upgrade(alembic_config, AFTER_MERGE)

        with migration_engine.connect() as connection:
            remaining = connection.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('contest_session_problems_status', 'contest_session_result')
            """)).scalars().all()

        assert remaining == []

    def test_seen_problem_primary_key_is_restored_after_deduplication(
        self, migration_engine, alembic_config
    ):
        """
        a81e39f8ee47 dropped a column that participated in the composite primary
        key, which drops the whole constraint. Duplicates could accumulate after
        that, so they are removed before the key goes back on.
        """
        command.upgrade(alembic_config, BEFORE_MERGE)
        _insert_old_shape_rows(migration_engine)
        command.upgrade(alembic_config, AFTER_MERGE)

        with migration_engine.connect() as connection:
            primary_key_columns = connection.execute(text("""
                SELECT a.attname
                FROM pg_constraint c
                JOIN pg_attribute a
                  ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                WHERE c.conrelid = 'contest_session_seen_problem'::regclass
                  AND c.contype = 'p'
                ORDER BY a.attname
            """)).scalars().all()

            seen_rows = connection.execute(text(
                "SELECT count(*) FROM contest_session_seen_problem"
            )).scalar_one()

        assert primary_key_columns == ["cf_problem_contestID", "cf_problem_index", "session_id"]
        # ('111','A') was inserted twice and must survive exactly once
        assert seen_rows == 2

    def test_history_indexes_exist(self, migration_engine, alembic_config):
        """
        The previous set was dropped by autogenerate because it existed only in a
        migration. These are declared on the model too.
        """
        command.upgrade(alembic_config, BEFORE_MERGE)
        command.upgrade(alembic_config, AFTER_MERGE)

        with migration_engine.connect() as connection:
            indexes = connection.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'contest_session'
            """)).scalars().all()

        assert "ix_contest_session_user_id_status" in indexes
        assert "ix_contest_session_user_id_status_starts_at" in indexes

    def test_downgrade_restores_the_child_tables(self, migration_engine, alembic_config):
        """
        The downgrade has to genuinely work, otherwise the upgrade is a one-way
        door with no way back if something is wrong in production.
        """
        command.upgrade(alembic_config, BEFORE_MERGE)
        _insert_old_shape_rows(migration_engine)
        command.upgrade(alembic_config, AFTER_MERGE)
        command.downgrade(alembic_config, BEFORE_MERGE)

        with migration_engine.connect() as connection:
            statuses = connection.execute(text("""
                SELECT problem_number, "problem_contestID", problem_index,
                       problem_rating, status, accepted_at, solved_in_min
                FROM contest_session_problems_status
                WHERE session_id = :sid
                ORDER BY problem_number
            """), {"sid": SESSION_ID}).all()

            result = connection.execute(text("""
                SELECT solved_count, performance, rating_before, rating_after, rating_delta
                FROM contest_session_result WHERE session_id = :sid
            """), {"sid": SESSION_ID}).one()

        assert len(statuses) == 4
        assert statuses[0].problem_rating == 1100
        assert statuses[0].status == "SOLVED"
        assert statuses[0].accepted_at == "1700000300"
        assert statuses[0].solved_in_min == 5
        assert statuses[2].status == "UNSOLVED"
        assert statuses[2].accepted_at is None

        # solved_count is not stored after the merge, so it is recomputed
        assert result.solved_count == 2
        assert result.performance == 1650
        assert result.rating_after == 1417
