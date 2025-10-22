from api.user.user_response_models import (
    UserInfoResponse
)
from starlette import status
from fastapi import HTTPException
import logging
from api.config import get
import jwt

from api.db.pg_database import SessionLocal
from api.error_constants import ErrorConstants
from api.user.user_model import User

logger = logging.getLogger(__name__)

def get_user_info(token: str) -> UserInfoResponse:
    
    logger.info(f"Validating token")

    user_detail = _validate_token_and_get_user_detail(token)

    logger.info(f"Successfully validated token and got user detail: {user_detail}")

    try:
        with SessionLocal() as db_session:
            user = db_session.query(User).filter(User.id == user_detail["id"]).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.USER_NOT_FOUND)
            user_info = UserInfoResponse(
                user_id=str(user.id),
                username=user.username,
                codeforces_handle=user.codeforces_handle
            )
            return user_info
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to get user info with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)


def update_codeforces_handle_service(codeforces_handle: str, token: str) -> bool:

    logger.info("Validating token")

    user_detail = _validate_token_and_get_user_detail(token)

    logger.info("Successfully validated token")

    try:
        with SessionLocal() as db_session:
            user = db_session.query(User).filter(User.id == user_detail["id"]).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.USER_NOT_FOUND)
            user.codeforces_handle = codeforces_handle
            db_session.commit()
            db_session.refresh(user)
            return True
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to update codeforces handle with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)

    
def _validate_token_and_get_user_detail(token: str) -> bool:
    if not token or not jwt.decode(token, get("JWT_SECRET_KEY"), algorithms=[get("JWT_ALGORITHM")]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ErrorConstants.UNAUTHORIZED)
    return jwt.decode(token, get("JWT_SECRET_KEY"), algorithms=[get("JWT_ALGORITHM")])