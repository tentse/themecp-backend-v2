import time
import uuid

import structlog
from fastapi import Request

from api.logging_config import get_logger

logger = get_logger(__name__)


async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    logger.info("request.start")
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception("request.error", duration_ms=duration_ms)
        structlog.contextvars.clear_contextvars()
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request.end",
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    structlog.contextvars.clear_contextvars()
    return response
