from api.user.user_model import User
from api.db.pg_database import SessionLocal
from uuid import UUID

from fastapi import HTTPException
from starlette import status
from api.error_constants import ErrorConstants
import logging

logger = logging.getLogger(__name__)

def get_user_by_id_repository(user_id: UUID) -> User:
    try:
        with SessionLocal() as db_session:
            user = db_session.query(User).filter(User.id == user_id).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.USER_NOT_FOUND)
            return user
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to get user by id with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)

def update_codeforces_handle_repository(user_id: UUID, codeforces_handle: str) -> bool:
    try:
        with SessionLocal() as db_session:
            user = db_session.query(User).filter(User.id == user_id).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.USER_NOT_FOUND)
            user.codeforces_handle = codeforces_handle
            db_session.commit()
            db_session.refresh(user)
            return True
    except HTTPException as e:
        raise e

def get_user_by_username_repository(username: str) -> User:
    try:
        with SessionLocal() as db_session:
            user = db_session.query(User).filter(User.username == username).first()
            return user
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to get user by username with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)