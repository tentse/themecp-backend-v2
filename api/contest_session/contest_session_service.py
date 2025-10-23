from api.contest_session.contest_session_response_model import (
    ContestSessionResponse,
    Problem
)

from api.contest_session.contest_session_repository import (
    fetch_problems_from_codeforces_repository,
    save_contest_session_repository,
    get_user_solved_problems_on_codeforces_repository
)

from api.user.user_service import (
    _validate_token_and_get_user_detail
)

from api.contest_level.contest_level_service import (
    get_contest_level_service
)
from api.contest_level.contest_level_response_model import (
    ContestLevelResponse
)

from fastapi import HTTPException
from starlette import status
import logging
from api.error_constants import ErrorConstants
from typing import List

logger = logging.getLogger(__name__)

def create_contest_session_service(
    contest_level: int,
    contest_theme: str,
    token: str
) -> ContestSessionResponse:
    
    user_detail = _validate_token_and_get_user_detail(token)

    try:
        contest_level_detail = get_contest_level_service(contest_level=contest_level)

        user_solved_problems: List[str] = _get_user_solved_problems_service(
            user_codeforces_handle = user_detail.codeforces_handle
        )

        problems: List[Problem] = _get_problems_service(
            contest_theme = contest_theme,
            contest_level_detail = contest_level_detail,
            user_solved_problems = user_solved_problems
        )

        save_contest_session = save_contest_session_repository(
            user_id = user_detail.id,
            contest_level = contest_level,
            contest_theme = contest_theme,
            contest_duration = contest_level_detail.duration,
            problems = problems
        )

        return ContestSessionResponse(
            id = str(save_contest_session.id),
            user_id = str(user_detail.id),
            contest_level = save_contest_session.contest_level,
            contest_theme = save_contest_session.contest_theme,
            start_time = None,
            end_time = None,
            duration = save_contest_session.duration,
            rating_1 = save_contest_session.rating_1,
            rating_2 = save_contest_session.rating_2,
            rating_3 = save_contest_session.rating_3,
            rating_4 = save_contest_session.rating_4,
            t1 = None,
            t2 = None,
            t3 = None,
            t4 = None,
            problem_1_id = save_contest_session.problem_1_id,
            problem_2_id = save_contest_session.problem_2_id,
            problem_3_id = save_contest_session.problem_3_id,
            problem_4_id = save_contest_session.problem_4_id,
            problem_1_index = save_contest_session.problem_1_index,
            problem_2_index = save_contest_session.problem_2_index,
            problem_3_index = save_contest_session.problem_3_index,
            problem_4_index = save_contest_session.problem_4_index,
            status = save_contest_session.status,
            problem_listed = save_contest_session.problem_listed,
            date = save_contest_session.date,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to get contest level with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)
            

def _get_user_solved_problems_service(
    user_codeforces_handle: str
) -> List[str]:
    try:
        user_solved_problems = get_user_solved_problems_on_codeforces_repository(
            user_codeforces_handle = user_codeforces_handle
        )
        return [
            f"{problem.get('contestId')}-{problem.get('index')}"
            for problem in user_solved_problems
        ]
    except HTTPException as e:
        raise e

def _get_problems_service(
    contest_level_detail: ContestLevelResponse,
    contest_theme: str,
    user_solved_problems: List[str]
) -> List[Problem]:

    try:
        selected_problems: List[Problem] = []
        codeforces_problems = fetch_problems_from_codeforces_repository(
            theme = contest_theme
        )
        for i in range(1, 5):
            problem = _fetch_problem_from_codeforces_service(
                rating = getattr(contest_level_detail, f"rating_{i}"),
                user_solved_problems = user_solved_problems,
                problems = codeforces_problems
            )
            selected_problems.append(
                Problem(
                    problem_number = i,
                    problem_id = problem.problem_id,
                    problem_index = problem.problem_index,
                    problem_rating = int(problem.problem_rating),
                )
            )
        return selected_problems
    except HTTPException as e:
        raise e

def _fetch_problem_from_codeforces_service(
    rating: int,
    user_solved_problems: List[str],
    problems: any
) -> Problem:
    try:
        for problem in problems:
            if problem.get('rating', None) != None and problem.get('rating') == rating:
                problem_id_and_index = f"{problem.get('contestId')}-{problem.get('index')}"
                if problem_id_and_index not in user_solved_problems:
                    user_solved_problems.append(f"{problem.get('contestId')}-{problem.get('index')}")
                    return Problem(
                        problem_id = str(problem.get('contestId')),
                        problem_index = problem.get('index'),
                        problem_rating = int(problem.get('rating')),
                    )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.UNSOLVED_PROBLEM_NOT_FOUND)

    except HTTPException as e:
        raise e

