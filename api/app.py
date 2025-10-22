import logging
from logging.config import dictConfig

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette import status

from api.auth.auth_views import auth_router
from api.user.user_views import user_router

# Configure application logging to ensure module logs appear in the console
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s [%(name)s] %(levelname)s: %(message)s",
            "use_colors": None,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
        }
    },
    "loggers": {
        # Root logger catches all loggers (including api.*)
        "": {"handlers": ["console"], "level": "INFO"},
        # Keep uvicorn loggers at INFO
        "uvicorn": {"level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"level": "INFO"},
    },
}

dictConfig(LOGGING_CONFIG)

api = FastAPI(
    title="ThemeCP Backend V2",
    description="This is the second version of ThemeCP backend",
    root_path="/api/v2",
    redoc_url="/docs",
)


api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api.include_router(auth_router)
api.include_router(user_router)

@api.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}