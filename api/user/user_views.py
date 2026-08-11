from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    Query
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
    CodeforcesHandleUpdate,
    LeaderboardEntry
)
from .user_services import UserService

DbSession = Annotated[Session, Depends(get_db)]

# How many users the leaderboard shows when the caller does not say. Change the
# board size by passing ?limit=, or by changing this default.
LEADERBOARD_DEFAULT_LIMIT = 10
LEADERBOARD_MAX_LIMIT = 100

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@users_router.get("", status_code=200)
def get_user_details(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(HTTPBearer(auto_error=False))
    ] = None,
    codeforces_handle: Annotated[
        str | None,
        Query(description="View user's profile")
    ] = None,
) -> UserResponseModel:
    """
    Get a user profile.
    """
    return UserService.get_user_profile(
        db=db,
        token=credentials.credentials if credentials else None,
        codeforces_handle=codeforces_handle
    )

@users_router.get("/leaderboard", status_code=200)
def get_leaderboard(
    db: DbSession,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=LEADERBOARD_MAX_LIMIT,
            description="How many users to return, highest rated first"
        )
    ] = LEADERBOARD_DEFAULT_LIMIT,
) -> list[LeaderboardEntry]:
    """
    Get the top rated users, highest first.
    """
    return UserService.get_leaderboard(db=db, limit=limit)


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
