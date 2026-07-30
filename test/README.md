# Integration Tests

This directory contains integration tests for the ThemeCP Backend V2 API.

## Overview

The integration tests use:
- **Docker**: PostgreSQL database container for isolated testing
- **Alembic**: Database migrations applied automatically
- **Mocked APIs**: Codeforces API calls are mocked to avoid external dependencies

## Prerequisites

1. **Docker and Docker Compose** must be installed and running
2. **Python dependencies** installed via Poetry:
   ```bash
   poetry install
   ```

## Running Tests

### Run all integration tests

```bash
poetry run pytest test/
```

### Run specific test file

```bash
poetry run pytest test/integration/test_user_flow.py
```

### Run with verbose output

```bash
poetry run pytest test/ -v
```

### Run with coverage report

```bash
poetry run pytest test/ --cov=api --cov-report=html
```

## Test Structure

### Fixtures (`test/conftest.py`)

The test configuration provides several fixtures:

- **`docker_compose`**: Manages Docker container lifecycle (session-scoped)
- **`test_db_url`**: Provides test database connection string
- **`run_migrations`**: Applies Alembic migrations to test database (session-scoped)
- **`test_engine`**: SQLAlchemy engine for test database (session-scoped)
- **`db`**: Per-test SQLAlchemy session bound to a connection-level transaction that rolls back at teardown. Pass this as `db=db` to any direct service/repository call.
- **`api_client`**: FastAPI TestClient with `get_db` overridden to share the `db` session
- **`mock_codeforces_api`**: Mocks Codeforces API calls (function-scoped)

### Test Database

The test database configuration:
- **Host**: localhost
- **Port**: 5433 (to avoid conflict with local DB on 5432)
- **Database**: `themecp_v2_test`
- **User**: `themecp_test`
- **Password**: `themecp_test`

The database container is defined in `local_setup/docker-compose.yml` as the `pg_db_test` service.

## Writing Tests

### Basic Example

```python
def test_user_registration(api_client, db, mock_codeforces_api):
    """Test user registration via the HTTP endpoint."""
    response = api_client.post("/auth/register", json={"email": "test@example.com"})
    assert response.status_code == 201
```

### Using Database Session

Services and repositories take a `db: Session` as their first argument. Pass the `db` fixture to call them directly:

```python
def test_database_operation(api_client, db):
    user = UserRepository.get_user_by_email(db=db, email="test@example.com")
    assert user is not None
```

### Customizing Codeforces API Mocks

You can customize mock responses in your tests:

```python
def test_custom_codeforces_response(api_client, db, mock_codeforces_api):
    # Customize the mock response
    def custom_mock(url, **kwargs):
        mock_response = Mock()
        if "/user.status" in url:
            mock_response.json.return_value = {
                "status": "OK",
                "result": [/* custom data */]
            }
        return mock_response
    
    mock_codeforces_api.side_effect = custom_mock
    
    # Your test code here
```

## Test Isolation

- Each test runs in its own database transaction
- Transactions are automatically rolled back after each test
- The Docker container is started once per test session and stopped after all tests complete
- Migrations run once per test session

## Environment Variables

Tests automatically set:
- `PG_DATABASE_URL`: Points to test database

You may need to set:
- `SECRET_KEY`: For JWT token generation (defaults can be set in test files)

## Troubleshooting

### Docker container fails to start

- Ensure Docker is running: `docker ps`
- Check if port 5433 is already in use
- Verify docker-compose file exists at `local_setup/docker-compose.yml`

### Database connection errors

- Wait for container to be ready (fixture handles this automatically)
- Check Docker container logs: `docker logs themecp-v2-pg-db-test`

### Migration errors

- Ensure all Alembic migration files are present
- Check that `alembic.ini` is in the project root

### Mock not working

- Ensure you're using the `mock_codeforces_api` fixture
- Check that you're patching the correct module path

## CI/CD Integration

These tests are designed to run in CI/CD environments:

1. Docker must be available in the CI environment
2. Tests automatically manage container lifecycle
3. No manual setup required beyond installing dependencies

Example GitHub Actions workflow:

```yaml
- name: Run integration tests
  run: |
    poetry install
    poetry run pytest test/ -v
```
