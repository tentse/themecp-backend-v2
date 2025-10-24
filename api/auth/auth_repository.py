from sqlite3 import IntegrityError

from fastapi import HTTPException

from starlette import status

from api.db.pg_database import SessionLocal

from api.user.user_model import User
from api.error_constants import ErrorConstants

def save_user_to_database(username: str, password: str, codeforces_handle: str) -> User:
    try:
        with SessionLocal() as db_session:
            user = User(
                username=username,
                password=password,
                codeforces_handle=codeforces_handle
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            return user
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ErrorConstants.USER_ALREADY_EXISTS)