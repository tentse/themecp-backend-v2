from api.user.user_response_models import (
    UserInfoResponse
)
from starlette import status
from fastapi import HTTPException
import logging
from api.config import get
import jwt

from uuid import UUID

from api.error_constants import ErrorConstants
from api.user.user_model import User

from api.user.user_repository import (
    get_user_by_id_repository,
    update_codeforces_handle_repository
)

logger = logging.getLogger(__name__)

def get_user_info(token: str) -> UserInfoResponse:
    
    logger.info(f"Validating token")

    user_detail = _validate_token_and_get_user_detail(token)

    logger.info(f"Successfully validated token and got user detail: {user_detail}")

    try:
        user_info = UserInfoResponse(
            user_id=str(user_detail.id),
            username=user_detail.username,
            codeforces_handle=user_detail.codeforces_handle
        )
        return user_info
    except HTTPException as e:
        raise e


def update_codeforces_handle_service(codeforces_handle: str, token: str) -> bool:

    logger.info("Validating token")

    user_detail = _validate_token_and_get_user_detail(token)

    logger.info("Successfully validated token")

    try:
        return update_codeforces_handle_repository(user_id=user_detail.id, codeforces_handle=codeforces_handle)
    except HTTPException as e:
        raise e

    
def _validate_token_and_get_user_detail(token: str) -> User:
    if not token or not jwt.decode(token, get("JWT_SECRET_KEY"), algorithms=[get("JWT_ALGORITHM")]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ErrorConstants.UNAUTHORIZED)
    user_detail = jwt.decode(token, get("JWT_SECRET_KEY"), algorithms=[get("JWT_ALGORITHM")])

    return get_user_by_id_repository(user_id=UUID(user_detail["id"]))