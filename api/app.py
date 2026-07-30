from api.sentry_init import init_sentry
init_sentry()

from api.logging_config import configure_logging
configure_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from api.contest_session.contest_session_views import contest_session_router
from api.contest_level.contest_level_views import contest_level_router
from api.auth.auth_views import auth_router
from api.user.user_views import users_router
from api.contest_theme.contest_theme_views import contest_theme_router
from api.middleware import logging_middleware
from api.config import get

api = FastAPI(
    title="ThemeCP Backend V2",
    description="This is the second version of ThemeCP backend",
    root_path="/api/v2",
    docs_url="/docs",      # Swagger UI at /api/v2/docs
    redoc_url="/redoc",    # ReDoc at /api/v2/redoc
)

# Credentials are enabled, so the origin list must be explicit — a wildcard
# origin combined with allow_credentials lets any site read authenticated
# responses on a user's behalf.
_cors_origins = [
    origin.strip()
    for origin in get("CORS_ALLOW_ORIGINS").split(",")
    if origin.strip() and origin.strip() != "*"
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.middleware("http")(logging_middleware)

# Include routers
api.include_router(auth_router)
api.include_router(users_router)
api.include_router(contest_session_router)
api.include_router(contest_level_router)
api.include_router(contest_theme_router)


@api.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}


# TO RUN SERVER: poetry run uvicorn api.app:api --reload
# Alembic commands:
#   poetry run alembic revision --autogenerate -m "migration_name"
#   poetry run alembic upgrade head