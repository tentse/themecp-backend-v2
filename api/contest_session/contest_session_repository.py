from api.config import get
import requests

from api.error_constants import ErrorConstants
from fastapi import HTTPException
from starlette import status
import logging

from api.contest_session.contest_session_model import ContestSession
from typing import List
from uuid import UUID

from api.db.pg_database import SessionLocal

from api.contest_session.contest_session_response_model import (
    Problem
)

logger = logging.getLogger(__name__)

def fetch_problems_from_codeforces_repository(theme: str):
    try:
        problems = requests.get(f"{get('CODEFORCE_API_URL')}/problemset.problems?tags={theme}")
        return problems.json()['result']['problems']
    except Exception as e:
        logger.error("Failed to fetch problems from codeforces with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.CODEFORCES_API_ERROR)

def get_user_solved_problems_on_codeforces_repository(user_codeforces_handle: str):
    try:
        user_solved_problems = requests.get(f"{get('CODEFORCE_API_URL')}/user.status?handle={user_codeforces_handle}")
        return user_solved_problems.json()['result']
    except Exception as e:
        logger.error("Failed to get user solved problems on codeforces with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.CODEFORCES_API_ERROR)

def save_contest_session_repository(user_id: UUID,contest_level: int, contest_theme: str, contest_duration: int, problems: List[Problem]) -> ContestSession:
    try:
        with SessionLocal() as db_session:
            new_contest_session = ContestSession(
                user_id = user_id,
                contest_level = contest_level,
                contest_theme = contest_theme,
                duration = contest_duration,
                rating_1 = problems[0].problem_rating,
                rating_2 = problems[1].problem_rating,
                rating_3 = problems[2].problem_rating,
                rating_4 = problems[3].problem_rating,
                problem_1_id = problems[0].problem_id,
                problem_2_id = problems[1].problem_id,
                problem_3_id = problems[2].problem_id,
                problem_4_id = problems[3].problem_id,
                problem_1_index = problems[0].problem_index,
                problem_2_index = problems[1].problem_index,
                problem_3_index = problems[2].problem_index,
                problem_4_index = problems[3].problem_index,
                status = "review",
                problem_listed = [
                    f"{problem.problem_id}-{problem.problem_index}"
                    for problem in problems
                ]
            )
            db_session.add(new_contest_session)
            db_session.commit()
            db_session.refresh(new_contest_session)
            return new_contest_session
    except Exception as e:
        logger.error("Failed to save contest session with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)