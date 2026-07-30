from typing import Annotated
from fastapi import (
    APIRouter,
    Depends
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from sqlalchemy.orm import Session
from api.db.pg_database import get_db
from .auth_response_models import (
    Credentials,
    AuthResponseModel
)
from .auth_services import AuthService

security = HTTPBearer()

DbSession = Annotated[Session, Depends(get_db)]

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@auth_router.post("/register", status_code=201)
def register(
    credentials: Credentials,
    db: DbSession,
) -> AuthResponseModel:
    """
    Register a new user.
    """
    return AuthService.auth_register_service(
        db=db,
        email=credentials.email
    )


@auth_router.post("/login", status_code=200)
def login(
    credentials: Credentials,
    db: DbSession,
) -> AuthResponseModel:
    """
    Login an existing user.
    """
    return AuthService.auth_login_service(
        db=db,
        email=credentials.email
    )
