import math
import time
from fastapi import HTTPException
from sqlalchemy.orm import Session
from api.error_constants import ErrorConstants
from api.user.user_response_models import (
    UserResponseModel,
)
from . import contest_session_models as ContestSessionModels
from . import contest_session_response_models as ContestSessionResponseModels
from api.codeforces import codeforces_response_model as CodeforcesResponseModel
from api.contest_level import contest_level_response_models as ContestLevelResponseModels
from api.contest_level.contest_level_services import ContestLevelService
from .contest_session_repository import ContestSessionRepository
from api.utils import Utils
from api.user.user_services import UserService
from api.user.user_repository import UserRepository
from api.codeforces.codeforces_utils import CodeforcesUtils
from api.cache import cache
from api.utils import Utils
from pydantic import ValidationError

CONTEST_SESSION_CACHE_KEY_PREFIX = "contest_session"

class ContestSessionService:


    @staticmethod
    def get_contest_session_service(db: Session, token: str) -> ContestSessionResponseModels.ContestSessionOutput:
        """
        get contest session detail by user id
        """

        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)

        user_id: str = user_detail.id
        contest_session_detail = ContestSessionRepository.get_contest_session_in_review_or_running(
            db=db,
            user_id=user_id
        )

        if contest_session_detail is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorConstants.CONTEST_SESSION_NOT_FOUND
            )

        return ContestSessionService._build_contest_session_output(
            db=db,
            user_id=user_id,
            contest_session_detail=contest_session_detail
        )


    @staticmethod
    def get_rating_plot_data(
        db: Session,
        token: str | None,
        codeforces_rating: bool = False,
        user_id: str | None = None
    ) -> ContestSessionResponseModels.RatingPlot:
        """
        Get rating plot for the user themecp and codeforces
        """

        cache_key = f"{CONTEST_SESSION_CACHE_KEY_PREFIX}:{user_id}:cf_rating{codeforces_rating}"
        cache_data = cache.get(cache_key)
        if cache_data is not None:
            try:
                return ContestSessionResponseModels.RatingPlot.model_validate(cache_data)
            except ValidationError:
                cache.delete(cache_key)

        user_detail, _ = UserService.resolve_profile_user(
            db=db,
            token=token,
            user_id=user_id
        )
        user_id: str = user_detail.id

        raw_themecp = ContestSessionRepository.get_user_themecp_contest_ratings_with_date(
            db=db,
            user_id=user_id
        )
        themecp_ratings: list[ContestSessionResponseModels.RatingPlotItem] = [
            ContestSessionResponseModels.RatingPlotItem(date=date_str, rating=rating, rating_delta=rating_delta)
            for date_str, rating, rating_delta in raw_themecp
        ]

        codeforces_ratings: list[ContestSessionResponseModels.RatingPlotItem] = []
        if codeforces_rating and user_detail.codeforces_handle:
            raw_cf = CodeforcesUtils.get_user_rating_history(
                codeforces_handle=user_detail.codeforces_handle
            )
            codeforces_ratings = [
                ContestSessionResponseModels.RatingPlotItem(date=date_str, rating=rating, rating_delta=rating_delta)
                for date_str, rating, rating_delta in raw_cf
            ]

        response = ContestSessionResponseModels.RatingPlot(
            themecp_ratings=themecp_ratings,
            codeforces_ratings=codeforces_ratings,
        )

        cache.set(cache_key, response.model_dump_json(), ttl=150)

        return response


    @staticmethod
    def get_heatgraph_data(
        db: Session,
        token: str | None,
        year: int,
        user_id: str | None = None
    ) -> ContestSessionResponseModels.HeatgraphData:
        """
        Get heatgraph data: contest attempt count per date for the user within the given year (FINISHED sessions only).
        """

        cache_key = f"{CONTEST_SESSION_CACHE_KEY_PREFIX}:{user_id}:year{year}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            try:
                return ContestSessionResponseModels.HeatgraphData.model_validate(cached_data)
            except ValidationError:
                cache.delete(cache_key)
        
        user_detail, _ = UserService.resolve_profile_user(
            db=db,
            token=token,
            user_id=user_id
        )
        user_id: str = user_detail.id
        raw = ContestSessionRepository.get_user_contest_attempts_by_date(db=db, user_id=user_id, year=year)
        items = [
            ContestSessionResponseModels.HeatgraphDataItem(date=date_str, contest_attempts=count)
            for date_str, count in raw
        ]
        response = ContestSessionResponseModels.HeatgraphData(items=items)

        cache.set(cache_key, response.model_dump_json(), ttl=150)

        return response


    @staticmethod
    def get_contest_history(
        db: Session,
        token: str | None,
        skip: int,
        limit: int,
        user_id: str | None = None
    ) -> ContestSessionResponseModels.ContestHistoryOutput:
        """
        Get a user's contest history (FINISHED sessions only), paginated, latest first.
        """
        cache_key = f"{CONTEST_SESSION_CACHE_KEY_PREFIX}:{user_id}:skip-{skip}:limit-{limit}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            try:
                return ContestSessionResponseModels.ContestHistoryOutput.model_validate(cached_data)
            except ValidationError:
                cache.delete(cache_key)
        
        user_detail, _ = UserService.resolve_profile_user(
            db=db,
            token=token,
            user_id=user_id
        )
        user_id: str = user_detail.id

        rows, total_count = ContestSessionRepository.get_user_contest_history_paginated(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        items: list[ContestSessionResponseModels.ContestHistoryItem] = []

        for session in rows:
            starts_at = session.starts_at

            # Everything below comes off the row we already fetched, so the
            # loop issues no queries at all.
            problem_statuses = session.problem_slots()
            status_map = {ps.problem_number: ContestSessionResponseModels.ProblemStatus(ps.status) for ps in problem_statuses}
            solved_in_min_map = {
                ps.problem_number: ps.solved_in_min if ps.status == ContestSessionResponseModels.ProblemStatus.SOLVED.value else None
                for ps in problem_statuses
            }

            contest_history_item: ContestSessionResponseModels.ContestHistoryItem = ContestSessionService._build_contest_history_item(
                session=session,
                starts_at=starts_at,
                status_map=status_map,
                solved_in_min_map=solved_in_min_map
            )
            items.append(contest_history_item)

        response = ContestSessionResponseModels.ContestHistoryOutput(
            items=items,
            skip=skip,
            limit=limit,
            total=total_count
        )

        cache.set(cache_key, response.model_dump_json(), 150)

        return response


    @staticmethod
    def _build_contest_history_item(
        session,
        starts_at: str,
        status_map: dict[int, ContestSessionResponseModels.ProblemStatus],
        solved_in_min_map: dict[int, int | None]
    ) -> ContestSessionResponseModels.ContestHistoryItem:
        """
        Build a contest history item from a finished session.

        Ratings come from the session's own snapshot rather than from
        contest_levels, so editing a level does not retroactively rewrite the
        ratings shown for contests already played.
        """
        return ContestSessionResponseModels.ContestHistoryItem(
            session_id=session.id,
            date=Utils.unix_timestamp_to_date_str(starts_at),
            level=session.level,
            theme=session.theme,
            duration_in_min=session.duration_in_min,
            performance=session.performance,
            rating=session.rating_after,
            rating_delta=session.rating_delta,
            p1=ContestSessionResponseModels.ProblemDetail(
                contestId=session.p1_cf_contestId,
                index=session.p1_cf_index,
                rating=session.p1_rating
            ),
            p2=ContestSessionResponseModels.ProblemDetail(
                contestId=session.p2_cf_contestId,
                index=session.p2_cf_index,
                rating=session.p2_rating
            ),
            p3=ContestSessionResponseModels.ProblemDetail(
                contestId=session.p3_cf_contestId,
                index=session.p3_cf_index,
                rating=session.p3_rating
            ),
            p4=ContestSessionResponseModels.ProblemDetail(
                contestId=session.p4_cf_contestId,
                index=session.p4_cf_index,
                rating=session.p4_rating
            ),
            p1_status=status_map.get(1, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p2_status=status_map.get(2, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p3_status=status_map.get(3, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p4_status=status_map.get(4, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p1_solved_in_min=solved_in_min_map.get(1),
            p2_solved_in_min=solved_in_min_map.get(2),
            p3_solved_in_min=solved_in_min_map.get(3),
            p4_solved_in_min=solved_in_min_map.get(4),
        )


    @staticmethod
    def create_contest_session(
        db: Session,
        create_contest_session: ContestSessionResponseModels.ContestSessionInput,
        token: str
    ) -> ContestSessionResponseModels.ContestSessionOutput:
        """
        Service function to create a new contest session.
        """

        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)
        user_id: str = user_detail.id

        if user_detail.codeforces_handle is None:
            raise HTTPException(
                status_code=400,
                detail=ErrorConstants.CODEFORCES_HANDLE_NOT_ADDED
            )

        # Check for existing active session (REVIEW or RUNNING)
        contest_session_in_review_or_running = ContestSessionRepository.get_contest_session_in_review_or_running(db=db, user_id=user_id)

        if contest_session_in_review_or_running is not None:
            return ContestSessionService._build_contest_session_output(
                db=db,
                user_id=user_id,
                contest_session_detail=contest_session_in_review_or_running
            )

        session_id = Utils.generate_id()

        contest_level: ContestLevelResponseModels.ContestLevelOutput = ContestLevelService.get_problem_level_ratings(
            db=db,
            level=create_contest_session.level
        )

        selected_problems: list[ContestSessionResponseModels.ProblemDetail] = ContestSessionService._select_problems_for_contest_session(
            db=db,
            session_id=session_id,
            codeforces_handle=user_detail.codeforces_handle,
            theme=create_contest_session.theme,
            contest_level=contest_level
        )

        problems = [
            (selected_problems[0].contestId, selected_problems[0].index),
            (selected_problems[1].contestId, selected_problems[1].index),
            (selected_problems[2].contestId, selected_problems[2].index),
            (selected_problems[3].contestId, selected_problems[3].index)
        ]

        saved_contest_session = ContestSessionRepository.save_contest_session_and_seen_problems_to_db(
            db=db,
            session_id=session_id,
            user_id=user_id,
            level=create_contest_session.level,
            theme=create_contest_session.theme,
            duration_in_min=contest_level.duration_in_min,
            status=ContestSessionResponseModels.ContestStatus.REVIEW.value,
            problems=problems
        )
        db.commit()
        db.refresh(saved_contest_session)

        return ContestSessionResponseModels.ContestSessionOutput(
            id=saved_contest_session.id,
            status=saved_contest_session.status,
            user_id=saved_contest_session.user_id,
            level=saved_contest_session.level,
            theme=saved_contest_session.theme,
            duration_in_min=saved_contest_session.duration_in_min,
            p1=selected_problems[0],
            p2=selected_problems[1],
            p3=selected_problems[2],
            p4=selected_problems[3],
        )


    @staticmethod
    def _build_contest_session_output(db: Session, user_id: str, contest_session_detail) -> ContestSessionResponseModels.ContestSessionOutput:

        contest_level: ContestLevelResponseModels.ContestLevelOutput = ContestLevelService.get_problem_level_ratings(
            db=db,
            level=contest_session_detail.level
        )

        return ContestSessionResponseModels.ContestSessionOutput(
            id=contest_session_detail.id,
            status=contest_session_detail.status,
            user_id=user_id,
            starts_at=contest_session_detail.starts_at,
            ends_at=contest_session_detail.ends_at,
            level=contest_session_detail.level,
            theme=contest_session_detail.theme,
            duration_in_min=contest_session_detail.duration_in_min,
            p1=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session_detail.p1_cf_contestId,
                index=contest_session_detail.p1_cf_index,
                rating=contest_level.p1_rating
            ),
            p2=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session_detail.p2_cf_contestId,
                index=contest_session_detail.p2_cf_index,
                rating=contest_level.p2_rating
            ),
            p3=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session_detail.p3_cf_contestId,
                index=contest_session_detail.p3_cf_index,
                rating=contest_level.p3_rating
            ),
            p4=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session_detail.p4_cf_contestId,
                index=contest_session_detail.p4_cf_index,
                rating=contest_level.p4_rating
            )
        )


    @staticmethod
    def _select_problems_for_contest_session(
        db: Session,
        session_id: str,
        theme: str,
        codeforces_handle: str,
        contest_level: ContestLevelResponseModels.ContestLevelOutput
    ) -> list[ContestSessionResponseModels.ProblemDetail]:
        """
        Select 4 problems for a contest session based on the contest level.
        """
        codeforces_problems: list[CodeforcesResponseModel.CodeforcesProblems] = CodeforcesUtils.get_codeforces_problems()

        contest_level_ratings = [
            contest_level.p1_rating,
            contest_level.p2_rating,
            contest_level.p3_rating,
            contest_level.p4_rating
        ]

        # Batch-load seen problems once to avoid N+1 queries
        seen_problems: set[tuple[str, str]] = ContestSessionRepository.get_seen_problems_for_session(
            db=db,
            session_id=session_id
        )

        user_attempted_problems_from_codeforces: set[tuple[str, str]] = CodeforcesUtils.get_user_attempted_problems(
            codeforces_handle=codeforces_handle
        )

        selected_problems: list[ContestSessionResponseModels.ProblemDetail] = []
        for i in range(4):
            selected_problem = ContestSessionService._fetch_problem_by_rating_and_tags(
                codeforces_problems=codeforces_problems,
                rating=contest_level_ratings[i],
                theme=theme,
                seen_problems=seen_problems,
                user_attempted_problems_from_codeforces=user_attempted_problems_from_codeforces
            )
            selected_problems.append(selected_problem)
            # Add newly selected problem to seen set to avoid duplicates
            if selected_problem:
                seen_problems.add((selected_problem.contestId, selected_problem.index))

        return selected_problems


    @staticmethod
    def _fetch_problem_by_rating_and_tags(
        codeforces_problems: list[CodeforcesResponseModel.CodeforcesProblems],
        rating: int,
        theme: str,
        seen_problems: set[tuple[str, str]],
        user_attempted_problems_from_codeforces: set[tuple[str, str]]
    ) -> ContestSessionResponseModels.ProblemDetail:
        """
        Helper function to fetch a problem by rating and tags.

        Args:
            codeforces_problems: List of available Codeforces problems
            rating: Target problem rating
            theme: Target problem theme/tag
            seen_problems: Set of (contestID, index) tuples for already seen problems

        Returns:
            ProblemDetail for a matching unseen problem
        """
        # First try to find a problem matching both rating and theme
        for problem in codeforces_problems:
            problem_key = (problem.contestID, problem.index)
            if problem.rating == rating and theme in problem.tags and problem_key not in seen_problems and problem_key not in user_attempted_problems_from_codeforces:
                return ContestSessionResponseModels.ProblemDetail(
                    contestId=problem.contestID,
                    index=problem.index,
                    rating=problem.rating
                )

        # If no problem is found with the theme, return any problem with the rating
        for problem in codeforces_problems:
            problem_key = (problem.contestID, problem.index)
            if problem.rating == rating and problem_key not in seen_problems and problem_key not in user_attempted_problems_from_codeforces:
                return ContestSessionResponseModels.ProblemDetail(
                    contestId=problem.contestID,
                    index=problem.index,
                    rating=problem.rating
                )


    @staticmethod
    def re_roll_contest_session_problem(
        db: Session,
        contest_session_id: str,
        problem_number: int,
        token: str
    ) -> ContestSessionResponseModels.ContestSessionOutput:
        """
        Re-roll a problem in a contest session.
        """
        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)
        contest_session = ContestSessionRepository.get_contest_session_by_id_and_user_id(
            db=db,
            user_id=user_detail.id,
            session_id=contest_session_id
        )
        if contest_session.status != ContestSessionResponseModels.ContestStatus.REVIEW.value:
            raise HTTPException(
                status_code=409,
                detail=ErrorConstants.CONTEST_SESSION_NOT_REVIEW
            )

        if problem_number not in [1, 2, 3, 4]:
            raise HTTPException(
                status_code=400,
                detail=ErrorConstants.INVALID_PROBLEM_NUMBER
            )

        contest_level: ContestLevelResponseModels.ContestLevelOutput = ContestLevelService.get_problem_level_ratings(
            db=db,
            level=contest_session.level
        )

        selected_problems: list[ContestSessionResponseModels.ProblemDetail] = ContestSessionService._select_problems_for_contest_session(
            db=db,
            session_id=contest_session.id,
            codeforces_handle=user_detail.codeforces_handle,
            theme=contest_session.theme,
            contest_level=contest_level
        )

        contest_session = ContestSessionRepository.update_contest_session_problem_db_and_seen_problems_db(
            db=db,
            session_id=contest_session.id,
            problem_number=problem_number,
            problem_contestId=selected_problems[problem_number - 1].contestId,
            problem_index=selected_problems[problem_number - 1].index
        )
        db.commit()
        db.refresh(contest_session)

        return ContestSessionService._build_contest_session_output(
            db=db,
            user_id=contest_session.user_id,
            contest_session_detail=contest_session
        )


    @staticmethod
    def delete_contest_session_in_review_status(
        db: Session,
        contest_session_id: str,
        token: str
    ) -> None:
        """
        Delete a contest session in REVIEW status.
        """
        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)
        contest_session = ContestSessionRepository.get_contest_session_by_id_and_user_id(
            db=db,
            user_id=user_detail.id,
            session_id=contest_session_id
        )
        if contest_session.status != ContestSessionResponseModels.ContestStatus.REVIEW.value:
            raise HTTPException(
                status_code=409,
                detail=ErrorConstants.CONTEST_SESSION_NOT_REVIEW
            )
        ContestSessionRepository.delete_contest_session(
            db=db,
            session_id=contest_session.id
        )
        db.commit()
        return None


    @staticmethod
    def start_contest_session_service(db: Session, contest_session_id: str, token: str) -> ContestSessionResponseModels.ContestSessionOutput:
        """
        Start a contest session with 15-second countdown.

        This method:
        1. Gets the user's session in REVIEW status
        2. Calculates start time (current time + 15 seconds)
        3. Calculates end time (start time + duration_in_min)
        4. Updates session to RUNNING status
        5. Creates problem status records for tracking

        Args:
            contest_session_id: The contest session ID
            token: JWT authentication token

        Returns:
            StartContestResponse with session info and start time
        """
        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)

        # Get user's REVIEW session
        contest_session = ContestSessionRepository.get_contest_session_by_id_and_user_id(
            db=db,
            user_id=user_detail.id,
            session_id=contest_session_id
        )
        if contest_session.status == ContestSessionResponseModels.ContestStatus.RUNNING.value:
            raise HTTPException(
                status_code=409,
                detail=ErrorConstants.CONTEST_SESSION_ALREADY_RUNNING
            )

        # Calculate start time (current time + 15 seconds for countdown)
        # Using Unix timestamp in seconds to match Codeforces submission time format
        starts_at = int(time.time()) + 15
        ends_at = starts_at + (contest_session.duration_in_min * 60)

        # Get contest level for problem ratings
        contest_level: ContestLevelResponseModels.ContestLevelOutput = ContestLevelService.get_problem_level_ratings(
            db=db,
            level=contest_session.level
        )

        # Start the contest and create problem status records
        ContestSessionRepository.start_contest_session(
            db=db,
            session_id=contest_session.id,
            starts_at=starts_at,
            ends_at=ends_at,
            ratings=[
                contest_level.p1_rating,
                contest_level.p2_rating,
                contest_level.p3_rating,
                contest_level.p4_rating,
            ]
        )
        db.commit()

        contest_session_output: ContestSessionResponseModels.ContestSessionOutput = ContestSessionService._build_contest_session_output(
            db=db,
            user_id=contest_session.user_id,
            contest_session_detail=contest_session
        )

        contest_session_output.status = ContestSessionResponseModels.ContestStatus.RUNNING
        contest_session_output.starts_at = starts_at
        contest_session_output.ends_at = ends_at

        return contest_session_output


    @staticmethod
    def refresh_problem_status_service(
        db: Session,
        token: str,
        contest_session_id: str
    ) -> ContestSessionResponseModels.ContestSessionProblemsStatus:
        """
        Refresh problem statuses by checking Codeforces submissions.

        Top-level entry point — commits at the end.
        """
        result = ContestSessionService._do_refresh_problem_status(
            db=db,
            token=token,
            contest_session_id=contest_session_id
        )
        db.commit()
        return result


    @staticmethod
    def _do_refresh_problem_status(
        db: Session,
        token: str,
        contest_session_id: str
    ) -> ContestSessionResponseModels.ContestSessionProblemsStatus:
        """
        Internal helper that performs problem-status refresh without committing.
        Used by refresh_problem_status_service and end_contest_session so that
        end_contest_session can commit all its writes atomically.
        """
        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)

        contest_session = ContestSessionRepository.get_contest_session_by_id_and_user_id(
            db=db,
            user_id=user_detail.id,
            session_id=contest_session_id
        )

        if contest_session.status != ContestSessionResponseModels.ContestStatus.RUNNING.value:
            raise HTTPException(
                status_code=409,
                detail=ErrorConstants.CONTEST_SESSION_NOT_RUNNING
            )

        contest_level: ContestLevelResponseModels.ContestLevelOutput = ContestLevelService.get_problem_level_ratings(
            db=db,
            level=contest_session.level
        )

        problem_statuses = ContestSessionRepository.get_problem_statuses_by_id(
            db=db,
            session_id=contest_session.id
        )

        starts_at: int = contest_session.starts_at

        user_submissions = CodeforcesUtils.get_user_submitted_problems(
            codeforces_handle=user_detail.codeforces_handle,
            skip=1,
            limit=100
        )
        accepted_submissions = ContestSessionService._build_lookup_of_accepted_submissions(
            user_submissions=user_submissions,
            starts_at=starts_at
        )
        ContestSessionService._check_problems_solve_sequentially_and_update_problem_statuses(
            db=db,
            session_id=contest_session.id,
            problem_statuses=problem_statuses,
            accepted_submissions=accepted_submissions,
            starts_at=starts_at
        )

        # Map problem statuses to p1_status through p4_status
        status_map = {ps.problem_number: ContestSessionResponseModels.ProblemStatus(ps.status) for ps in problem_statuses}

        return ContestSessionResponseModels.ContestSessionProblemsStatus(
            contest_session_id=contest_session.id,
            starts_at=contest_session.starts_at,
            ends_at=contest_session.ends_at,
            p1=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session.p1_cf_contestId,
                index=contest_session.p1_cf_index,
                rating=contest_level.p1_rating
            ),
            p2=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session.p2_cf_contestId,
                index=contest_session.p2_cf_index,
                rating=contest_level.p2_rating
            ),
            p3=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session.p3_cf_contestId,
                index=contest_session.p3_cf_index,
                rating=contest_level.p3_rating
            ),
            p4=ContestSessionResponseModels.ProblemDetail(
                contestId=contest_session.p4_cf_contestId,
                index=contest_session.p4_cf_index,
                rating=contest_level.p4_rating
            ),
            p1_status=status_map.get(1, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p2_status=status_map.get(2, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p3_status=status_map.get(3, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
            p4_status=status_map.get(4, ContestSessionResponseModels.ProblemStatus.UNSOLVED),
        )


    @staticmethod
    def _build_lookup_of_accepted_submissions(
        user_submissions: list[CodeforcesResponseModel.UserSubmittedProblem],
        starts_at: int
    ) -> dict[tuple[str, str], int]:
        """
        Build a lookup of accepted submissions: (contestID, index) -> latest creationTimeSeconds
        """
        accepted_submissions: dict[tuple[str, str], int] = {}
        for submission in user_submissions:
            if submission.verdict == "OK" and submission.creationTimeSeconds >= starts_at:
                key = (submission.contestID, submission.index)
                if key not in accepted_submissions or submission.creationTimeSeconds > accepted_submissions[key]:
                    accepted_submissions[key] = submission.creationTimeSeconds

        return accepted_submissions


    @staticmethod
    def _check_problems_solve_sequentially_and_update_problem_statuses(
        db: Session,
        session_id: str,
        problem_statuses: list[ContestSessionModels.ProblemSlot],
        accepted_submissions: dict[tuple[str, str], int],
        starts_at: int
    ) -> None:
        """
        Check problems solve sequentially and update problem statuses.
        """
        last_valid_time: int = starts_at
        for problem_status in problem_statuses:
            if problem_status.status == ContestSessionResponseModels.ProblemStatus.SOLVED.value:
                if problem_status.accepted_at is not None:
                    last_valid_time = int(problem_status.accepted_at)
                continue

            problem_key = (problem_status.problem_contestId, problem_status.problem_index)

            if problem_key not in accepted_submissions:
                # Current problem not solved, stop checking further
                break

            submission_time = accepted_submissions[problem_key]
            if submission_time < last_valid_time:
                # Later problem solved before earlier one on Codeforces - do not count it or any later problem
                break

            solved_in_min = (submission_time - starts_at) // 60

            ContestSessionRepository.update_problem_status(
                db=db,
                session_id=session_id,
                problem_number=problem_status.problem_number,
                state=ContestSessionResponseModels.ProblemStatus.SOLVED.value,
                accepted_at=submission_time,
                solved_in_min=solved_in_min
            )

            # Update local object for response
            problem_status.status = ContestSessionResponseModels.ProblemStatus.SOLVED.value
            problem_status.accepted_at = submission_time
            problem_status.solved_in_min = solved_in_min
            last_valid_time = submission_time


    @staticmethod
    def _calculate_performance(
        level: int,
        problem_statuses: list
    ) -> int:
        """
        Calculate contest performance based on the level, problem ratings,
        and solve times.

        The formula uses two time-limit constants derived from the level:
        - time_limit: for problems 1-3 (capped between 135 and 195)
        - time_limit_all_solved: for when all 4 are solved (capped between 120 and 180)

        Performance depends on the highest problem solved:
        - 0 solved: p1_rating - 50
        - 1 solved: weighted avg of p1_rating and p2_rating by solve speed
        - 2 solved: weighted avg of p2_rating and p3_rating by solve speed
        - 3 solved: weighted avg of p3_rating and p4_rating by solve speed
        - 4 solved: weighted avg of p4_rating and (p4_rating + 400) + level bonus

        Args:
            level: Contest level number
            problem_statuses: List of problem status records ordered by problem_number

        Returns:
            Calculated performance as integer
        """
        p1_rating = problem_statuses[0].problem_rating
        p2_rating = problem_statuses[1].problem_rating
        p3_rating = problem_statuses[2].problem_rating
        p4_rating = problem_statuses[3].problem_rating

        t1 = problem_statuses[0].solved_in_min
        t2 = problem_statuses[1].solved_in_min
        t3 = problem_statuses[2].solved_in_min
        t4 = problem_statuses[3].solved_in_min

        time_limit = max(135, min(195, 135 + 2.5 * (level - 52)))
        time_limit_all_solved = max(120, min(180, 120 + 2.5 * (level - 52)))

        if t4 is not None:
            performance = (
                (t4 / time_limit_all_solved) * p4_rating
                + ((time_limit_all_solved - t4) / time_limit_all_solved) * (p4_rating + 400)
                + ((level - 1) % 4) * 12.5
            )
        elif t3 is not None:
            performance = (
                (t3 / time_limit) * p3_rating
                + ((time_limit - t3) / time_limit) * p4_rating
            )
        elif t2 is not None:
            performance = (
                (t2 / time_limit) * p2_rating
                + ((time_limit - t2) / time_limit) * p3_rating
            )
        elif t1 is not None:
            performance = (
                (t1 / time_limit) * p1_rating
                + ((time_limit - t1) / time_limit) * p2_rating
            )
        else:
            performance = p1_rating - 50

        return math.floor(performance + 0.5)


    @staticmethod
    def _calculate_rating(
        performance: int,
        last_rating: int | None,
        first_problem_solve_time: int | None
    ) -> int:
        """
        Calculate new rating based on performance and previous rating.

        - First contest (no previous rating): uses default base of 1400
        - No problems solved: rating can only decrease
        - At least one problem solved: standard weighted formula

        Args:
            performance: The calculated performance
            last_rating: User's previous TheMCP rating, or None if first contest
            first_problem_solve_time: Solve time of problem 1, or None if unsolved

        Returns:
            New rating as integer
        """
        default_starting_rating = 1400

        if last_rating is None:
            new_rating = performance / 15 + default_starting_rating * 14 / 15
        elif first_problem_solve_time is None:
            new_rating = min(
                last_rating,
                performance / 15 + last_rating * 14 / 15
            )
        else:
            new_rating = performance / 15 + last_rating * 14 / 15

        return math.floor(new_rating + 0.5)


    @staticmethod
    def end_contest_session(db: Session, token: str, contest_session_id: str) -> None:
        """
        End a contest session: auto-refresh, calculate performance and rating, save result.

        Runs as a single atomic transaction:
        1. Auto-refreshes problem statuses via Codeforces API
        2. Calculates performance and rating
        3. Saves the outcome onto the session
        4. Updates session status to FINISHED
        5. Updates user contest stats
        6. Commits everything together — a crash mid-flow rolls back all writes.
        """
        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)

        # Get running session first, then refresh problem statuses
        contest_session = ContestSessionRepository.get_contest_session_by_id_and_user_id(
            db=db,
            user_id=user_detail.id,
            session_id=contest_session_id
        )

        if contest_session.status != ContestSessionResponseModels.ContestStatus.RUNNING.value:
            raise HTTPException(
                status_code=409,
                detail=ErrorConstants.CONTEST_SESSION_NOT_RUNNING
            )

        ContestSessionService._do_refresh_problem_status(
            db=db,
            token=token,
            contest_session_id=contest_session.id
        )

        # Get updated problem statuses
        problem_statuses = ContestSessionRepository.get_problem_statuses_by_id(
            db=db,
            session_id=contest_session.id
        )

        # Calculate performance
        performance = ContestSessionService._calculate_performance(
            level=contest_session.level,
            problem_statuses=problem_statuses
        )

        # Get the user's last contest result for rating_before
        last_result = ContestSessionRepository.get_last_contest_result(
            db=db,
            user_id=user_detail.id
        )
        rating_before = last_result.rating_after if last_result else None

        # If no TheMCP rating, use Codeforces rating; if that is also null, use 1400
        if rating_before is None and user_detail.codeforces_handle:
            rating_before = CodeforcesUtils.get_user_rating(user_detail.codeforces_handle)
        effective_rating_before = rating_before if rating_before is not None else 1400

        # Calculate new rating
        first_problem_solve_time = problem_statuses[0].solved_in_min
        rating_after = ContestSessionService._calculate_rating(
            performance=performance,
            last_rating=effective_rating_before,
            first_problem_solve_time=first_problem_solve_time
        )

        rating_delta = rating_after - effective_rating_before

        # Save contest result and mark the session FINISHED in one write
        ContestSessionRepository.save_contest_result(
            db=db,
            session_id=contest_session.id,
            performance=performance,
            rating_before=effective_rating_before,
            rating_after=rating_after,
            rating_delta=rating_delta
        )

        user = UserRepository.get_user_by_id(db=db, user_id=user_detail.id)
        max_contest_rating = max(user.max_contest_rating or 0, rating_after)
        best_performance = max(user.best_performance or 0, performance)
        contest_attempts = (user.contest_attempts or 0) + 1
        UserRepository.update_user_contest_stats(
            db=db,
            user_id=user.id,
            contest_rating=rating_after,
            max_contest_rating=max_contest_rating,
            best_performance=best_performance,
            contest_attempts=contest_attempts
        )
        db.commit()
