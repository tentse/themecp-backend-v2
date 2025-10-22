import os

DEFAULTS = {
    "JWT_SECRET_KEY": "themecp-backend-v2",
    "JWT_ALGORITHM": "HS256",
    "JWT_ISSUER": "themecp-backend-v2",
    "JWT_EXPIRATION_DAYS": 30,
    "PG_DATABASE_URL": "postgresql://themecp:themecp@localhost:5432/themecp-v2",

    "CODEFORCE_API_URL": "https://codeforces.com/api"
}

def get(key: str) -> str:
    return os.environ.get(key, DEFAULTS.get(key))