from datetime import timezone, datetime, timedelta
from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from .auth_response_models import (
    AuthResponseModel
)
from api.user.user_services import UserService

from api.config import get


class AuthService:


    @staticmethod
    def auth_register_service(
        db: Session,
        email: str
    ) -> AuthResponseModel:
        """
        Service function to register a new user.
        """

        # Registration logic (e.g., save user to database) goes here.
        # For demonstration, we'll just generate a token.

        UserService.register_user_service(
            db=db,
            email=email
        )

        ACCESS_TOKEN_EXPIRE_MINUTES = int(get("ACCESS_TOKEN_EXPIRE_MINUTES"))

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        token = AuthService.create_access_token(
            data={
                "email": email
            },
            expires_delta=access_token_expires
        )

        return AuthResponseModel(token=token)


    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
        """Create a JWT token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=43200)

        to_encode.update({"exp": expire})

        SECRET_KEY = get("SECRET_KEY")
        ALGORITHM = get("ALGORITHM")

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return encoded_jwt


    @staticmethod
    def auth_login_service(
        db: Session,
        email: str
    ) -> AuthResponseModel:
        """
        Service function to login an existing user.
        """

        # Login logic (e.g., verify user credentials) goes here.
        # For demonstration, we'll just generate a token.

        UserService.get_user_by_email_service(
            db=db,
            email=email
        )

        ACCESS_TOKEN_EXPIRE_MINUTES = int(get("ACCESS_TOKEN_EXPIRE_MINUTES"))

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        token = AuthService.create_access_token(
            data={
                "email": email
            },
            expires_delta=access_token_expires
        )

        return AuthResponseModel(token=token)
