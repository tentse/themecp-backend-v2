from fastapi import HTTPException
from starlette import status
import logging
from api.error_constants import ErrorConstants
from typing import List
import time

from api.contest_session.contest_session_response_model import (
    ContestSessionResponse,
    Problem,
    StartContestSessionResponse
)

from api.contest_session.contest_session_repository import (
    fetch_problems_from_codeforces_repository,
    save_contest_session_repository,
    get_user_solved_problems_on_codeforces_repository,
    get_contest_session_by_id_repository,
    update_contest_session_problem_repository,
    update_start_contest_session_repository,
    delete_contest_session_repository
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



logger = logging.getLogger(__name__)

def get_contest_session_by_id_service(contest_session_id: str) -> ContestSessionResponse:
    try:
        contest_session = get_contest_session_by_id_repository(
            contest_session_id=contest_session_id
        )
        return ContestSessionResponse(
            id = str(contest_session.id),
            user_id = str(contest_session.user_id),
            contest_level = contest_session.contest_level,
            contest_theme = contest_session.contest_theme,
            start_time = contest_session.start_time,
            end_time = contest_session.end_time,
            duration = contest_session.duration,
            rating_1 = contest_session.rating_1,
            rating_2 = contest_session.rating_2,
            rating_3 = contest_session.rating_3,
            rating_4 = contest_session.rating_4,
            t1 = contest_session.t1,
            t2 = contest_session.t2,
            t3 = contest_session.t3,
            t4 = contest_session.t4,
            problem_1_id = contest_session.problem_1_id,
            problem_2_id = contest_session.problem_2_id,
            problem_3_id = contest_session.problem_3_id,
            problem_4_id = contest_session.problem_4_id,
            problem_1_index = contest_session.problem_1_index,
            problem_2_index = contest_session.problem_2_index,
            problem_3_index = contest_session.problem_3_index,
            problem_4_index = contest_session.problem_4_index,
            status = contest_session.status
        )
    except HTTPException as e:
        raise e

def update_contest_session_problem_service(contest_session_id: str, problem_number: int, problem_rating: int, token: str) -> Problem:

    user_detail = _validate_token_and_get_user_detail(token)

    try:
        contest_session = get_contest_session_by_id_repository(
            contest_session_id=contest_session_id
        )
        if contest_session.user_id != user_detail.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ErrorConstants.CONTEST_SESSION_DOES_NOT_BELONG_TO_USER)

        user_solved_problems_on_codeforces: List[str] = _get_user_solved_problems_on_codeforces_service(
            user_codeforces_handle = user_detail.codeforces_handle
        )

        codeforces_problems = fetch_problems_from_codeforces_repository(
            theme = contest_session.contest_theme
        )
        problem_presented_list_so_far: List[str] = contest_session.problem_listed
        updated_problems = _fetch_problem_from_codeforces_service(
            rating = problem_rating,
            user_solved_problems_on_codeforces = user_solved_problems_on_codeforces,
            problem_presented_list = problem_presented_list_so_far,
            problems = codeforces_problems
        )

        update_contest_session_problem_repository(
            contest_session_id = contest_session_id,
            problem_number = problem_number,
            problem_id = updated_problems.problem_id,
            problem_index = updated_problems.problem_index,
            problem_rating = updated_problems.problem_rating,
            problem_presented_list = problem_presented_list_so_far
        )

        return Problem(
            problem_number = problem_number,
            problem_id = updated_problems.problem_id,
            problem_index = updated_problems.problem_index,
            problem_rating = updated_problems.problem_rating,
        )
        

    except HTTPException as e:
        raise e


def create_contest_session_service(
    contest_level: int,
    contest_theme: str,
    token: str
) -> ContestSessionResponse:
    
    user_detail = _validate_token_and_get_user_detail(token)

    try:
        contest_level_detail = get_contest_level_service(contest_level=contest_level)

        user_solved_problems_on_codeforces: List[str] = _get_user_solved_problems_on_codeforces_service(
            user_codeforces_handle = user_detail.codeforces_handle
        )
        problem_presented_list_so_far: List[str] = []
        problems: List[Problem] = _get_problems_service(
            contest_theme = contest_theme,
            contest_level_detail = contest_level_detail,
            user_solved_problems_on_codeforces = user_solved_problems_on_codeforces,
            problem_presented_list_so_far = problem_presented_list_so_far
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
            

def _get_user_solved_problems_on_codeforces_service(
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
    user_solved_problems_on_codeforces: List[str],
    problem_presented_list_so_far: List[str]
) -> List[Problem]:

    try:
        selected_problems: List[Problem] = []
        codeforces_problems = fetch_problems_from_codeforces_repository(
            theme = contest_theme
        )
        for i in range(1, 5):
            problem = _fetch_problem_from_codeforces_service(
                rating = getattr(contest_level_detail, f"rating_{i}"),
                user_solved_problems_on_codeforces = user_solved_problems_on_codeforces,
                problem_presented_list = problem_presented_list_so_far,
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
    user_solved_problems_on_codeforces: List[str],
    problem_presented_list: List[str],
    problems: any
) -> Problem:
    try:
        for problem in problems:
            if problem.get('rating', None) != None and problem.get('rating') == rating:
                problem_id_and_index = f"{problem.get('contestId')}-{problem.get('index')}"
                if problem_id_and_index not in user_solved_problems_on_codeforces and problem_id_and_index not in problem_presented_list:
                    problem_presented_list.append(f"{problem.get('contestId')}-{problem.get('index')}")
                    return Problem(
                        problem_id = str(problem.get('contestId')),
                        problem_index = problem.get('index'),
                        problem_rating = int(problem.get('rating')),
                    )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorConstants.UNSOLVED_PROBLEM_NOT_FOUND)

    except HTTPException as e:
        raise e


def start_contest_session_service(contest_session_id: str, token: str) -> StartContestSessionResponse:

    user_detail = _validate_token_and_get_user_detail(token=token)

    try:
        contest_session = get_contest_session_by_id_repository(
            contest_session_id = contest_session_id
        )
        if contest_session.user_id != user_detail.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ErrorConstants.CONTEST_SESSION_DOES_NOT_BELONG_TO_USER)

        if contest_session.status != "review":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorConstants.CONTEST_SESSION_ALREADY_STARTED_OR_COMPLETED)

        current_time_in_unix = int(time.time())

        contest_start_time = current_time_in_unix + 15

        contest_end_time = contest_start_time + contest_session.duration

        updated_contest_session = update_start_contest_session_repository(
            contest_session_id = contest_session_id,
            contest_start_time = contest_start_time,
            contest_end_time = contest_end_time
        )

        response = StartContestSessionResponse(
            contest_session_id = str(updated_contest_session.id),
            contest_start_time = contest_start_time,
            contest_end_time = contest_end_time,
            duration = contest_session.duration,
            status = updated_contest_session.status
        )

        return response

    except HTTPException as e:
        raise e


def delete_contest_session_service(contest_session_id: str, token: str) -> None:

    user_detail = _validate_token_and_get_user_detail(token=token)

    try:
        delete_contest_session_repository(
            contest_session_id = contest_session_id,
            user_id = user_detail.id
        )
    except HTTPException as e:
        raise e