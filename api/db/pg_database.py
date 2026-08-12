from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from api.config import get, get_int
from api.logging_config import get_logger

logger = get_logger(__name__)

engine = create_engine(
    get("PG_DATABASE_URL"),
    pool_size=get_int("DB_POOL_SIZE"),
    max_overflow=get_int("DB_MAX_OVERFLOW"),
    pool_timeout=get_int("DB_POOL_TIMEOUT"),
    pool_recycle=get_int("DB_POOL_RECYCLE"),
    pool_pre_ping=True,
)

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("db.connect.success")
except Exception:
    logger.exception("db.connect.failed")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy session for the duration of one request.
    Rolls back on any uncaught exception, always closes.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()