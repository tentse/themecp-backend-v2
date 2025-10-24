from api.contest_level.contest_level_model import ContestLevel

from api.db.pg_database import SessionLocal

from fastapi import HTTPException
from starlette import status
from api.error_constants import ErrorConstants
import logging

logger = logging.getLogger(__name__)

def get_contest_level_repository(contest_level: int) -> ContestLevel:
    try:
        with SessionLocal() as db_session:
            contest_level_detail = db_session.query(ContestLevel).filter(ContestLevel.level == contest_level).first()
            if contest_level_detail is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.CONTEST_LEVEL_NOT_FOUND)
            return contest_level_detail
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to get contest level with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)