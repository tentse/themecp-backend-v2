from sqlite3 import IntegrityError

from fastapi import HTTPException

from starlette import status

from sqlalchemy.orm import Session

from api.user.user_model import User
from api.error_constants import ErrorConstants

def save_user_to_database(db: Session, user: User) -> User:
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ErrorConstants.USER_ALREADY_EXISTS)