from api.db.pg_database import SessionLocal
from api.user.user_model import User
from fastapi import HTTPException
from starlette import status
from api.error_constants import ErrorConstants

class UserUtils:
    
    @staticmethod
    def check_if_user_name_already_exists(username: str) -> bool:
        with SessionLocal() as db_session:
            user = db_session.query(User).filter(User.username == username).first()
            if user is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ErrorConstants.USER_ALREADY_EXISTS)