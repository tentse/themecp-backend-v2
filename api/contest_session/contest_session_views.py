from typing import Annotated
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from api.db.pg_database import get_db
from .contest_session_services import ContestSessionService
from .contest_session_response_models import (
    ContestSessionInput,
    ContestSessionOutput,
    ContestSessionProblemsStatus,
    ContestHistoryOutput,
    RatingPlot,
    HeatgraphData
)
from api.logging_config import get_logger

logger = get_logger(__name__)

contest_session_router = APIRouter(
    prefix="/contest-session",
    tags=["Contest Session"],
)

Credentials = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]

optional_security = HTTPBearer(auto_error=False)
OptionalCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(optional_security)
]

ProfileUserId = Annotated[
    str | None,
    Query(description="Whose contests to return. Omit for your own.")
]

DbSession = Annotated[Session, Depends(get_db)]

@contest_session_router.get("", status_code=200)
def get_contest_session(credentials: Credentials, db: DbSession) -> ContestSessionOutput:
    """
    Get contest session by user id
    """
    token = credentials.credentials
    return ContestSessionService.get_contest_session_service(
        db=db,
        token=token
    )


@contest_session_router.get("/rating-plot", status_code=200)
def get_rating_plot(
    db: DbSession,
    credentials: OptionalCredentials = None,
    codeforces_rating: Annotated[
        bool, Query(description="Whether to include codeforces rating in the plot")
    ] = False,
    user_id: ProfileUserId = None,
) -> RatingPlot:
    """
    Get rating plot for the user themecp and codeforces.

    Public when `user_id` is given; otherwise a token identifies the user.
    """
    return ContestSessionService.get_rating_plot_data(
        db=db,
        token=credentials.credentials if credentials else None,
        codeforces_rating=codeforces_rating,
        user_id=user_id
    )


@contest_session_router.get("/heatgraph-data", status_code=200)
def get_heatgraph_data(
    db: DbSession,
    year: Annotated[int, Query(description="Calendar year (UTC) to return heatgraph data for", ge=2000, le=2100)],
    credentials: OptionalCredentials = None,
    user_id: ProfileUserId = None,
) -> HeatgraphData:
    """
    Get heatgraph data for the user within the given year.

    Public when `user_id` is given; otherwise a token identifies the user.
    """
    return ContestSessionService.get_heatgraph_data(
        db=db,
        token=credentials.credentials if credentials else None,
        year=year,
        user_id=user_id
    )


@contest_session_router.get("/history", status_code=200)
def get_contest_history(
    db: DbSession,
    credentials: OptionalCredentials = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    user_id: ProfileUserId = None,
) -> ContestHistoryOutput:
    """
    Get a user's contest history (FINISHED sessions only), paginated, latest first.

    Public when `user_id` is given; otherwise a token identifies the user.
    """
    return ContestSessionService.get_contest_history(
        db=db,
        token=credentials.credentials if credentials else None,
        skip=skip,
        limit=limit,
        user_id=user_id
    )


@contest_session_router.post("", status_code=201)
def create_contest_session(
    create_contest_session: ContestSessionInput,
    credentials: Credentials,
    db: DbSession,
) -> ContestSessionOutput:
    """
    Create a new contest session.
    """
    token = credentials.credentials
    return ContestSessionService.create_contest_session(
        db=db,
        create_contest_session=create_contest_session,
        token=token
    )


@contest_session_router.put("/{contest_session_id}/re-roll-problem/{problem_number:int}", status_code=200)
def re_roll_contest_session_problem(
    contest_session_id: str,
    problem_number: int,
    credentials: Credentials,
    db: DbSession,
) -> ContestSessionOutput:
    """
    Re-roll a problem in a contest session.
    """
    token = credentials.credentials
    return ContestSessionService.re_roll_contest_session_problem(
        db=db,
        contest_session_id=contest_session_id,
        problem_number=problem_number,
        token=token
    )


@contest_session_router.delete("/{contest_session_id}", status_code=204)
def delete_contest_session_in_review_status(
    contest_session_id: str,
    credentials: Credentials,
    db: DbSession,
) -> None:
    """
    Delete a contest session in REVIEW status.
    """
    token = credentials.credentials
    return ContestSessionService.delete_contest_session_in_review_status(
        db=db,
        contest_session_id=contest_session_id,
        token=token
    )


@contest_session_router.put("/{contest_session_id}/start", status_code=200)
def start_contest_session(contest_session_id: str, credentials: Credentials, db: DbSession) -> ContestSessionOutput:
    """
    Start a contest session with 15-second countdown.

    This endpoint transitions a contest session from REVIEW to RUNNING status,
    sets the start time to 15 seconds from now, and initializes problem status
    tracking records.

    Returns:
        StartContestResponse with session_id, status, starts_at (Unix timestamp in seconds),
        and duration_in_min
    """
    token = credentials.credentials
    return ContestSessionService.start_contest_session_service(
        db=db,
        contest_session_id=contest_session_id,
        token=token
    )


@contest_session_router.put("/{contest_session_id}/refresh", status_code=200)
def refresh_problem_status(
    contest_session_id: str,
    credentials: Credentials,
    db: DbSession,
) -> ContestSessionProblemsStatus:
    """
    Refresh problem statuses by checking Codeforces submissions.

    This endpoint checks the user's recent Codeforces submissions to determine
    if any contest problems have been solved. Problems must be solved in order -
    a later problem is only marked SOLVED if all previous problems are already SOLVED.

    Returns:
        ContestSessionProblemsStatus with contest_session_id, starts_at, ends_at,
        p1-p4 (ProblemDetail), and p1_status-p4_status (ProblemStatus)
    """
    token = credentials.credentials
    return ContestSessionService.refresh_problem_status_service(
        db=db,
        token=token,
        contest_session_id=contest_session_id,
    )


@contest_session_router.put("/{contest_session_id}/end", status_code=204)
def end_contest_session(contest_session_id: str, credentials: Credentials, db: DbSession) -> None:
    """
    End a contest session.

    This endpoint auto-refreshes problem statuses by checking Codeforces submissions,
    calculates performance and rating, saves the result, and transitions the session
    to FINISHED status.

    """
    token = credentials.credentials
    ContestSessionService.end_contest_session(
        db=db,
        token=token,
        contest_session_id=contest_session_id
    )
