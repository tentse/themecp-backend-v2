from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from starlette import status

from api.contest_session.contest_session_response_model import (
    ContestSessionResponse
)

from api.contest_session.contest_session_service import (
    create_contest_session_service
)

contest_session_router = APIRouter(
    prefix="/contest_sessions",
    tags=["Contest Sessions"]
)

@contest_session_router.post("/create", status_code=status.HTTP_201_CREATED)
def create_contest_session(
    contest_level: int,
    contest_theme: str,
    authentication_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> ContestSessionResponse:
    return create_contest_session_service(
        contest_level=contest_level,
        contest_theme=contest_theme,
        token=authentication_credentials.credentials
    )