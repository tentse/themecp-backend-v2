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
from api.codeforces.codeforces_response_model import (
    CodeforcesProblems
)
from api.db.pg_database import get_db
from .user_response_models import (
    UserResponseModel,
    CodeforcesHandleUpdate
)
from .user_services import UserService

DbSession = Annotated[Session, Depends(get_db)]

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@users_router.get("", status_code=200)
def get_user_details(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: DbSession,
) -> UserResponseModel:
    """
    Get user details from the provided token.
    """
    return UserService.get_user_detail_from_token(
        db=db,
        token=credentials.credentials
    )

@users_router.get("/handle-verification-cf-problem", status_code=200)
def get_cf_problem_for_handle_verification(
    codeforces_handle: str,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: DbSession,
) -> CodeforcesProblems:
    """
    Get a Codeforces problem URL for handle verification for the authenticated user.
    """
    return UserService.get_codeforces_problem_for_handle_verification(
        db=db,
        codeforces_handle=codeforces_handle,
        token=credentials.credentials
    )


@users_router.put("/codeforces-handle", status_code=200)
def update_codeforces_handle(
    codeforces_handle_verification: CodeforcesHandleUpdate,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: DbSession,
) -> bool:
    """
    Update the Codeforces handle for the authenticated user after verification.
    """
    return UserService.update_codeforces_handle(
        db=db,
        token=credentials.credentials,
        codeforces_handle_verification=codeforces_handle_verification
    )
