from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from starlette import status

from api.contest_session.contest_session_response_model import (
    ContestSessionResponse,
    Problem,
    StartContestSessionResponse
)

from api.contest_session.contest_session_service import (
    create_contest_session_service,
    update_contest_session_problem_service,
    get_contest_session_by_id_service,
    start_contest_session_service,
    delete_contest_session_service
)

contest_session_router = APIRouter(
    prefix="/contest_sessions",
    tags=["Contest Sessions"]
)

@contest_session_router.get("/{contest_session_id}", status_code=status.HTTP_200_OK)
def get_contest_session_by_id(
    contest_session_id: str,
) -> ContestSessionResponse:

    return get_contest_session_by_id_service(
        contest_session_id=contest_session_id
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

@contest_session_router.put("/{contest_session_id}", status_code=status.HTTP_201_CREATED)
def update_contest_session_problem(
    contest_session_id: str,
    problem_number: int,
    problem_rating: int,
    authentication_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> Problem:
    return update_contest_session_problem_service(
        contest_session_id=contest_session_id,
        problem_number=problem_number,
        problem_rating=problem_rating,
        token=authentication_credentials.credentials
    )

@contest_session_router.put("/{contest_session_id}/start", status_code=status.HTTP_201_CREATED)
def start_contest_session(
    contest_session_id: str,
    authentication_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> StartContestSessionResponse:
    return start_contest_session_service(
        contest_session_id=contest_session_id,
        token=authentication_credentials.credentials
    )

@contest_session_router.delete("/{contest_session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contest_session(
    contest_session_id: str,
    authentication_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> None:
    return delete_contest_session_service(
        contest_session_id = contest_session_id,
        token = authentication_credentials.credentials
    )