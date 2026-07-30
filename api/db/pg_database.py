from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from api.config import get
from api.logging_config import get_logger

logger = get_logger(__name__)

engine = create_engine(get("PG_DATABASE_URL"))

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