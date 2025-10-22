import logging
import jwt

from fastapi import HTTPException
from starlette import status

from datetime import timezone, timedelta, datetime

from api.config import get

from api.auth.auth_response_models import (
    SignUpRequest,
    SignUpResponse,
    SignInResponse,
)

import re

from api.auth.auth_repository import (
    save_user_to_database
)

from api.user.user_utils import UserUtils

from api.utils import Utils

from api.error_constants import ErrorConstants

from api.user.user_model import User

logger = logging.getLogger(__name__)

def sign_in_user_service(username: str, password: str) -> SignInResponse:
    logger.info(f"Signing in user: {username}")

    hashed_password = Utils.get_hashed_value(password)

    try:
        user = UserUtils.get_user_by_username(username=username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ErrorConstants.USER_NOT_FOUND)
        if user.password != hashed_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ErrorConstants.INVALID_CREDENTIALS)
        access_token = _generate_token_user(user)
        return SignInResponse(
            user_id=str(user.id),
            username=user.username,
            access_token=access_token
        )
    except HTTPException as e:
        # Preserve intended HTTP errors (e.g., 401 for invalid credentials)
        raise e
    except Exception as e:
        logger.error("Failed to sign in user with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)

def sign_up_user_service(user_info: SignUpRequest) -> SignUpResponse:
    
    logging.info(f"Validating user name and password: {user_info.username}")
    _validate_user_name_and_password(username=user_info.username, password=user_info.password)
    logging.info(f"User name and password validated successfully")

    logger.info(f"Signing up user: {user_info.username}")

    logger.info(f"Checking if user name exists: {user_info.username}")
    UserUtils.check_if_user_name_already_exists(username=user_info.username)

    logger.info(f"Creating new user: {user_info.username}")

    saved_user = save_user_to_database(
        username=user_info.username,
        password=Utils.get_hashed_value(user_info.password),
        codeforces_handle=user_info.codeforces_handle
    )
    logger.info(f"Saved user to database: {saved_user.username}")
    access_token = _generate_token_user(user=saved_user)
    logger.info(f"Generated access token for user: {saved_user.username}")

    return SignUpResponse(
        user_id=str(saved_user.id),
        username=saved_user.username,
        access_token=access_token
    )

def _generate_token_user(user: User):
    data = _generate_token_data(user)
    access_token = _generate_access_token(data)
    return access_token

def _generate_access_token(data: dict):

    secret_key = get("JWT_SECRET_KEY")
    algorithm = get("JWT_ALGORITHM")

    token = jwt.encode(data, secret_key, algorithm=algorithm)
    return token

def _generate_token_data(user: User) -> dict:
    expiration_days = int(get("JWT_EXPIRATION_DAYS") or 30)
    expiration = datetime.now(timezone.utc) + timedelta(days=expiration_days)
    data = {
        "id": str(user.id),
        "username": user.username,
        "codeforces_handle": user.codeforces_handle,
        "issuer": get("JWT_ISSUER"),
        "datetime": datetime.now(timezone.utc).isoformat(),
        "exp": expiration
    }
    return data

def _validate_user_name_and_password(username: str, password: str) -> bool:

    if len(username) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must have at least 5 characters")
    if not re.search(r"[0-9]", username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must have at least one number")
    if not re.match(r"^[A-Za-z0-9_.]+$", username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must have only letters, numbers, underscores, and dots")
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must have at least 8 characters")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must have at least one number")
    if not re.search(r"[A-Za-z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must have at least one letter")
    return True