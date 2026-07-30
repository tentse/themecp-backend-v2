# ThemeCP Backend V2

A FastAPI REST API for **ThemeCP**, a competitive programming training platform.
It generates themed practice contests from real [Codeforces](https://codeforces.com)
problems, then tracks solves, timing, and performance across sessions.

## Status

> **⚠️ This project is not production-ready. See [Security](#security) before deploying it.**
>
> The authentication flow does not verify identity. Read that section first.

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

## API documentation

Interactive docs are served at `/api/v2/docs` (Swagger) and `/api/v2/redoc` when the
server is running. For a frontend-friendly REST reference with request/response shapes
and TypeScript types, see [`doc/api-v2.md`](doc/api-v2.md).

## Security

**This backend does not currently authenticate users.**

`POST /api/v2/auth/login` accepts an email address and returns a valid 30-day JWT without
verifying a password, a one-time code, or ownership of that email. Anyone who knows or
guesses a registered address can obtain full access to that account. There is no password
handling anywhere in the codebase — the login service was written as a placeholder and
never replaced.

Consequently:

- **Do not deploy this publicly as-is.**
- Run it locally, or behind an authenticating proxy, until the flow is replaced with
  verified magic-link/OTP or password authentication.

Administrative mutation endpoints are separately protected by `ADMIN_API_TOKEN` and fail
closed when it is unset. That guard is unaffected by the issue above.

If you find another security problem, please open an issue — or, for anything sensitive,
contact the maintainer directly rather than filing publicly.

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
