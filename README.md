# themecp-backend-v2
This is the second version of ThemeCP backend.

## Local setup (quick)

- **Prerequisites**
  - **Python** 3.12+
  - **Poetry**
  - **Docker Desktop** (or Docker + WSL2 on Windows)

- **Start PostgreSQL**
  ```bash
  docker compose -f local_setup/docker-compose.yml up -d
  ```

- **Install dependencies**
  ```bash
  poetry install
  ```

- **Run DB migrations**
  ```bash
  poetry run alembic upgrade head
  ```

- **Start API**
  ```bash
  poetry run uvicorn api.app:api --reload --port 8000
  ```

- **Verify**
  - Health: `http://localhost:8000/api/v2/health`
  - Docs: `http://localhost:8000/api/v2/docs`

## Configuration

- Works out of the box with defaults. Optional overrides via env vars:
  - `PG_DATABASE_URL` (default `postgresql://themecp:themecp@localhost:5432/themecp-v2`)
  - `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_EXPIRATION_DAYS`

## Useful commands

- **Run tests**
  ```bash
  poetry run pytest
  ```

- **Stop DB**
  ```bash
  docker compose -f local_setup/docker-compose.yml down
  ```

## Troubleshooting

- If port 5432 is in use, stop local Postgres or change the port in `local_setup/docker-compose.yml`.
- Ensure Docker Desktop is running and `poetry` is on your PATH.