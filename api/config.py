import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Plain stdlib logging, not api.logging_config: that module imports this one, so
# using it here would be a circular import. Config is also read before logging is
# configured, so anything logged from here goes to the default handler.
logger = logging.getLogger(__name__)

DEFAULTS = {
    "PG_DATABASE_URL": "postgresql://themecp:themecp@localhost:5432/themecp_v2",

    # --- Database connection pool -----------------------------------------
    # DB_POOL_SIZE + DB_MAX_OVERFLOW is the hard ceiling on connections this
    # process will open. It must stay below what the server allows, divided by
    # the number of uvicorn workers — exceeding it produces
    # "FATAL: too many connections" rather than queueing.
    #
    # Managed free tiers are the binding constraint: Aiven's free PostgreSQL
    # caps max_connections at 20, reserves 3 for superusers and runs its own
    # services on ~12 more, leaving roughly 5. A local Postgres allows 100, so
    # these can be raised well above the defaults when self-hosting.
    #
    # Size is kept warm and overflow is opened on demand, so a low pool_size on
    # a distant database means paying connection setup (~1.5s to Aiven) during
    # a traffic spike. Prefer raising DB_POOL_SIZE over DB_MAX_OVERFLOW.
    "DB_POOL_SIZE": 3,
    "DB_MAX_OVERFLOW": 2,

    # Seconds a request waits for a free connection before failing. The wait is
    # invisible to the caller until it expires, so a long timeout turns
    # saturation into slow requests rather than errors.
    "DB_POOL_TIMEOUT": 30,

    # Seconds before an idle connection is discarded and reopened. Managed
    # providers close idle connections server-side; recycling first means the
    # application never hands out one the server has already dropped.
    "DB_POOL_RECYCLE": 300,

    "CODEFORCE_API_URL": "https://codeforces.com/api",

    "ACCESS_TOKEN_EXPIRE_MINUTES": 43200,  # 30 days
    "ALGORITHM": "HS256",

    # Required by administrative mutation endpoints. Empty means "not
    # configured", and those endpoints refuse to serve rather than open up.
    "ADMIN_API_TOKEN": "",

    # Comma-separated allowed CORS origins. Credentials are enabled, so "*"
    # must not be used here.
    "CORS_ALLOW_ORIGINS": "http://localhost:3000",

    "ENV": "development",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "console",
    "SENTRY_DSN": "",

    # --- Leaderboard -------------------------------------------------------
    # How many users GET /users/leaderboard returns when the caller does not
    # pass ?limit=, and the largest value ?limit= will accept.
    "LEADERBOARD_DEFAULT_LIMIT": 20,
    "LEADERBOARD_MAX_LIMIT": 100,

    # Contests a user must have finished before they are ranked.
    "LEADERBOARD_MIN_CONTESTS": 10,

    # How recently a user must have finished a contest to stay on the board.
    # About six months.
    "LEADERBOARD_ACTIVE_WITHIN_DAYS": 183,
}

def get(key: str) -> str:
    return os.environ.get(key, DEFAULTS.get(key))


def get_int(key: str) -> int:
    """
    Read a numeric setting, falling back to its default.
    """
    raw = os.environ.get(key)

    if raw is not None and str(raw).strip():
        try:
            return int(str(raw).strip())
        except ValueError:
            logger.warning(
                "config.invalid_int key=%s value=%r — falling back to default %r",
                key, raw, DEFAULTS.get(key),
            )

    return int(DEFAULTS[key])