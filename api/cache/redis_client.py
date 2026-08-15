import redis

from api.config import get, get_int
from api.logging_config import get_logger

logger = get_logger(__name__)

_redis_url = get("REDIS_URL")

client: redis.Redis | None = None

if _redis_url:
    _pool = redis.ConnectionPool.from_url(
        _redis_url,
        decode_responses=True,
        # socket_timeout=get_int("REDIS_SOCKET_TIMEOUT"),
        # socket_connect_timeout=get_int("REDIS_SOCKET_TIMEOUT"),
        # max_connections=get_int("REDIS_MAX_CONNECTIONS"),
        health_check_interval=30,
        retry_on_timeout=True,
    )
    client = redis.Redis(connection_pool=_pool)

    try:
        client.ping()
        logger.info("redis.connect.success")
    except Exception:
        logger.exception("redis.connect.failed")
else:
    logger.info("redis.disabled", reason="REDIS_URL not set")


def is_available() -> bool:
    if client is None:
        return False
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False