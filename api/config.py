import os
from dotenv import load_dotenv

load_dotenv()

DEFAULTS = {
    "PG_DATABASE_URL": "postgresql://themecp:themecp@localhost:5432/themecp_v2",

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
}

def get(key: str) -> str:
    return os.environ.get(key, DEFAULTS.get(key))