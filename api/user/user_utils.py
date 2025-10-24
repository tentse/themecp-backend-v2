from api.user.user_repository import (
    get_user_by_username_repository
)
from api.user.user_model import User
from starlette import status
from fastapi import HTTPException
from api.error_constants import ErrorConstants

class UserUtils:
    
    @staticmethod
    def check_if_user_name_already_exists(username: str) -> bool:
        user: User = get_user_by_username_repository(username=username)
        if user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ErrorConstants.USER_ALREADY_EXISTS)
        return True

    @staticmethod
    def get_user_by_username(username: str) -> User:
        return get_user_by_username_repository(username=username)