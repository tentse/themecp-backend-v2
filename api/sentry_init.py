import logging

from api.config import get


def init_sentry() -> None:
    dsn = get("SENTRY_DSN")
    if not dsn:
        logging.getLogger(__name__).info("sentry.disabled reason=no_dsn")
        return

    import sentry_sdk
    from fastapi import HTTPException
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    def before_send(event, hint):
        exc_info = hint.get("exc_info") if hint else None
        if exc_info:
            exc = exc_info[1]
            if isinstance(exc, HTTPException) and exc.status_code < 500:
                return None
        return event

    sentry_sdk.init(
        dsn=dsn,
        environment=get("ENV"),
        traces_sample_rate=0.1,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        before_send=before_send,
    )
