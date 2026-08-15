import json
from typing import Any

import redis

from api.cache.redis_client import client
from api.logging_config import get_logger

logger = get_logger(__name__)

def get(key: str) -> str | None:
    if client is None:
        return None
    try:
        return client.get(key)
    except redis.RedisError:
        logger.warning("cache.get.failed", key=key)
        return None

def set(key: str, value: str, ttl: int | None = None) -> bool:
    if client is None:
        return False
    try:
        if ttl is not None:
            client.setex(key, ttl, value)
        else:
            client.set(key, value)
        return True
    except redis.RedisError:
        logger.warning("cache.set.failed", key=key)
        return False

def delete(*keys: str) -> int:
    if client is None or not keys:
        return 0
    try:
        return client.delete(*keys)
    except redis.RedisError:
        logger.warning("cache.delete.failed", keys=keys)
        return 0