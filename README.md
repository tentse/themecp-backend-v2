# ThemeCP Backend V2

A FastAPI REST API for **ThemeCP**, a competitive programming training platform.
It generates themed practice contests from real [Codeforces](https://codeforces.com)
problems, then tracks solves, timing, and performance across sessions.

## Public history

This repository is a sanitized public export of a project previously developed
privately. Public history begins with the import commit because the earlier
development history contained local database artifacts and is retained only in
a private archive.

## Features

- **Contest sessions** — themed contests assembled from Codeforces problems, with a
  `REVIEW → RUNNING → FINISHED` state machine, sequential solve enforcement, problem
  re-rolls, and performance/rating calculation
- **Codeforces integration** — problem fetching, handle verification, and submission
  polling to confirm solves
- **Contest themes and levels** — difficulty tiers and topic-based problem selection
- **User profiles** — accounts linked to a verified Codeforces handle

## Tech stack

FastAPI · Python 3.12+ · PostgreSQL · SQLAlchemy 2.x · Alembic · Poetry

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker and Docker Compose (for PostgreSQL)

## Setup

1. **Install dependencies**

   ```bash
   poetry install
   ```

2. **Start local PostgreSQL**

   ```bash
   docker compose -f local_setup/docker-compose.yml up -d pg_db_local
   ```

   This runs on `localhost:5432` with user `themecp`, password `themecp`, database
   `themecp_v2`. These are local development credentials only.

3. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   At minimum, set `SECRET_KEY` — it has no default and JWT signing fails without it:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Every other variable is documented in [`.env.example`](.env.example) and has a
   working local default. Two are worth calling out:

   - `CORS_ALLOW_ORIGINS` — comma-separated list of allowed frontend origins. Credentials
     are enabled, so `*` is rejected; list origins explicitly.
   - `ADMIN_API_TOKEN` — required by administrative endpoints such as
     `POST /contest-theme`. While unset, those endpoints return `503`.

4. **Run migrations**

   ```bash
   poetry run alembic upgrade head
   ```

5. **Start the server**

   ```bash
   poetry run uvicorn api.app:api --reload
   ```

   - API base: `http://localhost:8000/api/v2`
   - Swagger UI: `http://localhost:8000/api/v2/docs`
   - ReDoc: `http://localhost:8000/api/v2/redoc`

## Tests

Tests need Docker — fixtures start a throwaway PostgreSQL on port 5433 automatically and
isolate each test by transaction rollback. Codeforces HTTP calls are mocked, so the suite
never touches the live API.

```bash
poetry run pytest test/
```

- Verbose: `poetry run pytest test/ -v`
- Coverage: `poetry run pytest test/ --cov=api --cov-report=html`
- Single file: `poetry run pytest test/integration/test_contest_session.py`

Fixture details and patterns are in [test/README.md](test/README.md).

## Architecture

The app is built with `root_path="/api/v2"`, so route paths declared in `*_views.py` do
**not** include that prefix — it only appears externally.

Each feature module under `api/` follows the same four-file layout:

| File | Responsibility |
| --- | --- |
| `*_views.py` | FastAPI router — HTTP shape, status codes, auth dependencies |
| `*_services.py` | Business logic and orchestration |
| `*_repository.py` | SQLAlchemy data access |
| `*_models.py` | ORM models |

Modules: `auth/`, `user/`, `contest_session/`, `contest_level/`, `contest_theme/`,
`codeforces/`. Cross-cutting helpers live in `api/db/`, `api/config.py`, and
`api/utils.py`.

All outbound Codeforces traffic goes through `CodeforcesUtils` in
[`api/codeforces/codeforces_utils.py`](api/codeforces/codeforces_utils.py) so tests can
intercept it in one place. Alembic is the source of truth for the schema.

## Contributing

Issues and pull requests are welcome.

- Follow the four-file module layout described in [Architecture](#architecture) rather
  than collapsing logic into views.
- Reuse the error strings in `api/error_constants.py` instead of inlining messages.
- Schema changes go through Alembic:
  `poetry run alembic revision --autogenerate -m "<name>"`.
- Add tests for new behavior and make sure `poetry run pytest test/` passes.
- Never commit real credentials or production data. `.env` is gitignored; put new
  configuration in [`.env.example`](.env.example) with a placeholder value.

## License

Released under the [MIT License](LICENSE).
