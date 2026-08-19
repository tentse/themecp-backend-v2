"""
Pytest configuration and fixtures for integration tests.

This module provides fixtures for:
- Docker container management (test database)
- Database sessions and migrations
- Codeforces API mocking
"""
import os
import subprocess
import time
import pytest
import redis
from typing import Generator
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from alembic import command
from alembic.config import Config

from api.auth import auth_response_models

# Test database configuration
TEST_DB_URL = "postgresql://themecp_test:themecp_test@localhost:5433/themecp_v2_test"

# Port 6380, not 6379: the suite gets its own Redis container, so a test run
# never flushes or evicts the cache you are developing against on redis_local.
TEST_REDIS_URL = "redis://localhost:6380/0"

DOCKER_COMPOSE_FILE = "local_setup/docker-compose.yml"
DOCKER_SERVICES = ["pg_db_test", "redis_test"]
MAX_WAIT_TIME = 60  # Maximum seconds to wait for DB to be ready

os.environ["PG_DATABASE_URL"] = TEST_DB_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL
os.environ["ADMIN_API_TOKEN"] = "test-admin-api-token"


def wait_for_db_ready(db_url: str, max_wait: int = MAX_WAIT_TIME) -> bool:
    """Wait for database to be ready by checking connection."""
    engine = create_engine(db_url)
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True
        except Exception:
            time.sleep(1)

    engine.dispose()
    return False


def wait_for_redis_ready(redis_url: str, max_wait: int = MAX_WAIT_TIME) -> bool:
    """Wait for Redis to be ready by polling PING."""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
            client.ping()
            client.close()
            return True
        except Exception:
            time.sleep(1)

    return False


# Client for the test cache, created once the container answers PING and reset
# on teardown. The flush fixture below uses it as a readiness flag too: while it
# is None there is no Redis to clear, so a unit-test-only run never pays a
# connection timeout per test.
_test_cache: redis.Redis | None = None


@pytest.fixture(scope="session")
def docker_compose():
    """
    Manage Docker Compose lifecycle for the test containers.

    Starts the test database and the test Redis before tests and stops both
    after.
    """
    global _test_cache

    # Start the test containers
    compose_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), DOCKER_COMPOSE_FILE)

    print("\n🚀 Starting test containers (PostgreSQL + Redis)...")
    result = subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "-d", *DOCKER_SERVICES],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to start Docker containers: {result.stderr}")

    def stop_containers():
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "stop", *DOCKER_SERVICES],
            capture_output=True
        )

    # Wait for database to be ready
    print("⏳ Waiting for database to be ready...")
    if not wait_for_db_ready(TEST_DB_URL):
        # Try to stop containers on failure
        stop_containers()
        raise RuntimeError("Database failed to become ready within timeout period")

    print("✅ Test database is ready")

    # Redis normally wins this race, but the suite must not start before it
    # answers PING. A late Redis would make the first tests miss the cache
    # silently rather than fail, which is the hardest kind of flake to trace.
    print("⏳ Waiting for Redis to be ready...")
    if not wait_for_redis_ready(TEST_REDIS_URL):
        stop_containers()
        raise RuntimeError("Redis failed to become ready within timeout period")

    _test_cache = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    print("✅ Test Redis is ready")

    yield

    # Cleanup: Stop the containers
    print("\n🛑 Stopping test containers...")
    if _test_cache is not None:
        _test_cache.close()
        _test_cache = None
    stop_containers()
    print("✅ Test containers stopped")


@pytest.fixture(autouse=True)
def flush_test_cache():
    """
    Clear the test cache before every test.

    Cached values sit above the patch point used by `mock_codeforces_api`, so
    without this one test's fake Codeforces payload would still be cached when
    the next test runs and the mock would never be consulted. Flushing before
    rather than after also gives a clean slate when a previous run was
    interrupted.
    """
    if _test_cache is not None:
        _test_cache.flushdb()
    yield


@pytest.fixture
def broken_redis():
    """
    Make every Redis command raise, simulating an unreachable server.

    api.cache.cache swallows redis.RedisError and reports a miss, so a request
    made while this fixture is active must still be served from the database.

    Patching the client rather than stopping the container keeps the test fast
    and leaves the rest of the session's cache untouched.
    """
    from api.cache import cache

    broken = Mock()
    for method in ("get", "set", "setex", "delete", "ttl", "scan_iter"):
        getattr(broken, method).side_effect = redis.ConnectionError("connection refused")

    with patch.object(cache, "client", broken):
        yield broken


@pytest.fixture(scope="session")
def test_db_url(docker_compose):
    """
    Return test database URL and set environment variable.

    This fixture ensures the test database container is running
    and sets PG_DATABASE_URL for Alembic migrations.
    """
    # Set environment variable for migrations and ensure SECRET_KEY is set
    os.environ["PG_DATABASE_URL"] = TEST_DB_URL
    if "SECRET_KEY" not in os.environ:
        os.environ["SECRET_KEY"] = "test-secret-key-for-integration-tests-only"
    return TEST_DB_URL


@pytest.fixture(scope="session")
def run_migrations(test_db_url):
    """
    Run Alembic migrations on the test database.

    This runs once per test session before any database-dependent tests.
    """
    # Get the project root directory (parent of test directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini = os.path.join(project_root, "alembic.ini")

    # Configure Alembic
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)

    print("🔄 Running Alembic migrations...")
    command.upgrade(alembic_cfg, "head")
    print("✅ Migrations completed")


@pytest.fixture(scope="session")
def test_engine(run_migrations):
    """
    Create SQLAlchemy engine for test database.

    This engine is used to create test sessions.
    """
    engine = create_engine(TEST_DB_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine) -> Generator[Session, None, None]:
    """
    Provide a database session for tests with automatic rollback.

    Each test gets a fresh session that rolls back after the test,
    ensuring test isolation.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    # Rollback transaction and close session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def mock_codeforces_api():
    """
    Mock Codeforces API calls.

    Provides default mock responses for:
    - /problemset.problems endpoint
    - /user.status endpoint

    Tests can override these by accessing the mock object.
    """
    # Default mock response for problemset.problems
    default_problems_response = {
        "status": "OK",
        "result": {
            "problems": [
                {
                    "contestId": 1236,
                    "index": "B",
                    "rating": 1700,
                    "tags": ["greedy"]
                },
                {
                    "contestId": 5000,
                    "index": "A",
                    "rating": 1000,
                    "tags": ["greedy", "dp"]
                },
                {
                    "contestId": 5000,
                    "index": "B",
                    "rating": 1200,
                    "tags": ["greedy", "dp"]
                },
                {
                    "contestId": 5000,
                    "index": "C",
                    "rating": 1400,
                    "tags": ["greedy", "dp"]
                },
                {
                    "contestId": 5000,
                    "index": "D",
                    "rating": 1600,
                    "tags": ["greedy", "dp"]
                },
                {
                    "contestId": 1234,
                    "index": "A",
                    "rating": 1500,
                    "tags": ["greedy", "math"]
                },
                {
                    "contestId": 1234,
                    "index": "B",
                    "rating": 1600,
                    "tags": ["dp", "graphs"]
                },
                {
                    "contestId": 5678,
                    "index": "A",
                    "rating": 1400,
                    "tags": ["implementation"]
                },
                {
                    "contestId": 5678,
                    "index": "B",
                    "rating": 1700,
                    "tags": ["greedy", "dp"]
                },
                # Extra problems per rating with "greedy" so multiple re-rolls each get a new one
                {"contestId": 9999, "index": "A", "rating": 1000, "tags": ["greedy"]},
                {"contestId": 9999, "index": "B", "rating": 1200, "tags": ["greedy"]},
                {"contestId": 9999, "index": "C", "rating": 1400, "tags": ["greedy"]},
                {"contestId": 9999, "index": "D", "rating": 1600, "tags": ["greedy"]},
                {"contestId": 8888, "index": "B", "rating": 1200, "tags": ["greedy"]},
            ]
        }
    }

    # Default mock response for user.status
    default_user_status_response = {
        "status": "OK",
        "result": [
            {
                "problem": {
                    "contestId": 1236,
                    "index": "B",
                    "rating": 1700,
                    "tags": ["greedy"]
                },
                "verdict": "COMPILATION_ERROR",
                "creationTimeSeconds": 1700000000
            },
            {
                "problem": {
                    "contestId": 1234,
                    "index": "A",
                    "rating": 1500,
                    "tags": ["greedy"]
                },
                "verdict": "OK",
                "creationTimeSeconds": 1700000100
            },
            {
                "problem": {
                    "contestId": 1234,
                    "index": "C",
                    "rating": 1800,
                    "tags": ["greedy"]
                },
                "verdict": "OK",
                "creationTimeSeconds": 1700000200
            },
            {
                "problem": {
                    "contestId": 1235,
                    "index": "B",
                    "rating": 1600,
                    "tags": ["greedy"]
                },
                "verdict": "OK",
                "creationTimeSeconds": 1700000300
            }
        ]
    }

    # Default mock response for user.info (rating null = unrated)
    default_user_info_response = {
        "status": "OK",
        "result": [
            {
                "handle": "test_user",
                "rating": None,
                "maxRating": None
            }
        ]
    }

    def mock_get(url, **kwargs):
        """Mock requests.get based on URL."""
        mock_response = Mock()

        if "/problemset.problems" in url:
            mock_response.json.return_value = default_problems_response
        elif "/user.status" in url:
            mock_response.json.return_value = default_user_status_response
        elif "/user.info" in url:
            mock_response.json.return_value = default_user_info_response
        else:
            mock_response.json.return_value = default_problems_response

        return mock_response

    # Patch requests.get in the codeforces_utils module
    with patch("api.codeforces.codeforces_utils.requests.get", side_effect=mock_get) as mock_patcher:
        yield mock_patcher


@pytest.fixture(scope="function")
def db(test_engine) -> Generator[Session, None, None]:
    """
    Per-test database session bound to an outer connection-level transaction.

    All repository/service work in the test runs through this session; at teardown
    we roll back the outer transaction so the DB is left clean for the next test.

    `join_transaction_mode="create_savepoint"` makes `session.commit()` release a
    SAVEPOINT instead of the outer transaction, so service-layer commits during a
    test don't leak across the rollback boundary.

    Direct service calls in tests/fixtures should pass `db=db`. HTTP requests through
    `api_client` reach this same session via the `get_db` dependency override.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autocommit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def api_client(db):
    """
    FastAPI TestClient bound to the test database.

    Overrides the `get_db` dependency so all HTTP requests share the same session
    as direct service calls in fixtures/tests. The override does NOT close the
    session at request end — the `db` fixture owns the lifecycle.
    """
    from api.app import api as fastapi_app
    from api.db.pg_database import get_db

    def override_get_db():
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        # No `finally: db.close()` — the `db` fixture owns cleanup.

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as client:
            yield client
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_headers():
    """Bearer header matching the ADMIN_API_TOKEN set for the test session."""
    return {"Authorization": "Bearer test-admin-api-token"}


@pytest.fixture
def dummy_user_without_codeforces_handle(db, api_client):
    """
    Dummy user for testing"
    """
    from api.auth.auth_services import AuthService

    email = "test_without_codeforces_handle@example.com"
    print("Registering dummy user")
    auth_response = AuthService.auth_register_service(
        db=db,
        email=email
    )
    print("Dummy user registered")
    token = auth_response.token

    yield {
        "email": email,
        "codeforces_handle": None,
        "token": token
    }


@pytest.fixture
def dummy_user_with_codeforces_handle(db, api_client):
    """
    Dummy user for testing"
    """
    from api.user.user_repository import UserRepository
    from api.auth.auth_services import AuthService

    email = "test_with_codeforces_handle@example.com"
    codeforces_handle = "cf_handle_example"
    print("Registering dummy user")
    auth_response = AuthService.auth_register_service(
        db=db,
        email=email
    )
    print("Dummy user registered")
    token = auth_response.token
    print("Updating dummy user codeforces handle")
    user = UserRepository.update_codeforces_handle_repository(
        db=db,
        email=email,
        codeforces_handle=codeforces_handle
    )
    db.commit()
    print("Dummy user codeforces_handle updated")

    yield {
        "email": email,
        "codeforces_handle": codeforces_handle,
        "token": token,
        "user_id": user.id,
    }


@pytest.fixture
def create_dummy_contest_level_20_and_21(db, api_client):
    """
    Create a dummy contest level for test
    """
    from api.contest_level.contest_level_services import ContestLevelService
    from api.contest_level.contest_level_response_models import ContestLevelInput

    contest_level = ContestLevelInput(
        level=21,
        duration_in_min=120,
        performance=1600,
        p1_rating=1000,
        p2_rating=1200,
        p3_rating=1400,
        p4_rating=1600
    )
    print("Creating contest level 21")
    contest_level = ContestLevelService.create_contest_level(
        db=db,
        create_contest_level=contest_level
    )
    print("Contest level created 21")

    contest_level = ContestLevelInput(
        level=20,
        duration_in_min=120,
        performance=1575,
        p1_rating=1000,
        p2_rating=1200,
        p3_rating=1400,
        p4_rating=1500
    )
    print("Creating contest level 20")
    contest_level = ContestLevelService.create_contest_level(
        db=db,
        create_contest_level=contest_level
    )
    print("Contest level created 20")


@pytest.fixture
def create_dummy_in_review_contest_session_level_21_theme_greedy(
    db,
    api_client,
    dummy_user_with_codeforces_handle,
    mock_codeforces_api,
    create_dummy_contest_level_20_and_21
):
    """
    Create a dummy contest session for a user
    """

    from api.contest_session.contest_session_response_models import (
        ContestSessionOutput,
        ContestSessionInput,
    )
    from api.contest_session.contest_session_services import ContestSessionService

    create_input = ContestSessionInput(level=21, theme="greedy")

    token = dummy_user_with_codeforces_handle['token']

    print("Creating contest session in review")
    response: ContestSessionOutput = ContestSessionService.create_contest_session(
        db=db,
        create_contest_session=create_input,
        token=token
    )
    print("Contest session created")

    yield {
        "token": token,
        "contest_session": response.model_dump()
    }


@pytest.fixture
def dummy_user_with_finished_contest_level_21_theme_greedy(
    db,
    api_client,
    dummy_user_with_codeforces_handle,
    mock_codeforces_api,
    create_dummy_contest_level_20_and_21,
):
    """
    User with at least one finished contest (1 problem solved).
    Used to test GET /users contest stats.
    """
    from unittest.mock import Mock

    request_body = {"level": 21, "theme": "greedy"}
    token = dummy_user_with_codeforces_handle["token"]

    create_resp = api_client.post(
        "/contest-session",
        json=request_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code in (200, 201)
    contest_session = create_resp.json()

    start_resp = api_client.post(
        "/contest-session/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start_resp.status_code in (200, 201)
    starts_at = start_resp.json()["starts_at"]

    p1 = contest_session["p1"]
    submissions = [
        {
            "contestId": int(p1["contestID"]),
            "index": p1["index"],
            "rating": p1["rating"],
            "verdict": "OK",
            "creationTimeSeconds": starts_at + 300,
            "tags": ["greedy"],
        }
    ]
    custom_user_status = {
        "status": "OK",
        "result": [
            {
                "problem": {
                    "contestId": s["contestId"],
                    "index": s["index"],
                    "rating": s.get("rating", 0),
                    "tags": s.get("tags", []),
                },
                "verdict": s["verdict"],
                "creationTimeSeconds": s["creationTimeSeconds"],
            }
            for s in submissions
        ],
    }
    original_side_effect = mock_codeforces_api.side_effect

    def custom_mock_get(url, **kwargs):
        mock_response = Mock()
        if "/user.status" in url:
            mock_response.json.return_value = custom_user_status
        else:
            return original_side_effect(url, **kwargs)
        return mock_response

    mock_codeforces_api.side_effect = custom_mock_get

    end_resp = api_client.post(
        "/contest-session/end",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert end_resp.status_code == 200
    end_data = end_resp.json()
    assert end_data["status"] == "FINISHED"

    yield {
        "email": dummy_user_with_codeforces_handle["email"],
        "codeforces_handle": dummy_user_with_codeforces_handle["codeforces_handle"],
        "token": token,
        "last_contest_rating": end_data["rating_after"],
        "max_contest_rating": end_data["rating_after"],
        "best_performance": end_data["performance"],
        "contest_attempts": 1,
        "rating_label": "Pupil",
    }


@pytest.fixture
def create_dummy_running_contest_session_level_21_theme_greedy(
    db,
    api_client,
    dummy_user_with_codeforces_handle,
    mock_codeforces_api,
    create_dummy_contest_level_20_and_21
):
    """
    Create a dummy contest session in RUNNING status for a user.
    First creates a session in REVIEW, then starts it.
    """
    from api.contest_session.contest_session_response_models import (
        ContestSessionOutput,
        ContestSessionInput,
    )
    from api.contest_session.contest_session_services import ContestSessionService

    create_input = ContestSessionInput(level=21, theme="greedy")

    token = dummy_user_with_codeforces_handle['token']

    print("Creating contest session in review")
    response: ContestSessionOutput = ContestSessionService.create_contest_session(
        db=db,
        create_contest_session=create_input,
        token=token
    )
    print("Contest session created")

    # Start the contest session
    print("Starting contest session")
    response: ContestSessionOutput = ContestSessionService.start_contest_session_service(
        db=db,
        contest_session_id=response.id,
        token=token
    )
    print("Contest session started")

    yield {
        "token": token,
        "contest_session": response.model_dump(),
    }
