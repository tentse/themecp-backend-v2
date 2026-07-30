from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from api.error_constants import ErrorConstants
from api.logging_config import get_logger
from .contest_session_response_models import (
    ContestStatus,
    ProblemStatus
)
from .contest_session_models import (
    ContestSession,
    ContestSessionSeenProblem,
    ContestSessionProblemsStatus,
    ContestSessionResult
)
from api.utils import Utils

logger = get_logger(__name__)


class ContestSessionRepository:


    @staticmethod
    def get_contest_session_by_id_and_user_id(db: Session, session_id: str, user_id: str) -> ContestSession:
        """
        Get contest session by ID.
        """
        try:
            session = db.query(ContestSession).filter(
                ContestSession.id == session_id,
                ContestSession.user_id == user_id
            ).first()
            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorConstants.CONTEST_SESSION_NOT_FOUND
                )
            return session
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_contest_session_by_id_and_user_id", session_id=session_id, user_id=user_id)
            raise HTTPException(status_code=503, detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_SESSION) from e


    @staticmethod
    def get_seen_problems_for_session(db: Session, session_id: str) -> set[tuple[str, str]]:
        """
        Batch-load all seen problems for a session.

        Args:
            session_id: The contest session ID

        Returns:
            Set of (contestID, index) tuples for all seen problems
        """
        try:
            seen_problems = db.query(ContestSessionSeenProblem).filter(
                ContestSessionSeenProblem.session_id == session_id
            ).all()

            return {
                (problem.cf_problem_contestId, problem.cf_problem_index)
                for problem in seen_problems
            }
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_seen_problems_for_session", session_id=session_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_SEEN_PROBLEMS
            ) from e


    @staticmethod
    def get_contest_session_in_review_or_running(db: Session, user_id: str) -> ContestSession:
        """
        Get user's contest session in REVIEW or RUNNING status.

        Args:
            user_id: The user ID

        Returns:
            ContestSession in REVIEW or RUNNING status

        Raises:
            HTTPException: 404 if no active session (REVIEW or RUNNING) found
        """
        try:
            contest_session = db.query(ContestSession).filter(
                ContestSession.user_id == user_id,
                ContestSession.status.in_([ContestStatus.REVIEW.value, ContestStatus.RUNNING.value])
            ).first()

            return contest_session
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_contest_session_in_review_or_running", user_id=user_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_SESSION
            ) from e


    @staticmethod
    def save_contest_session_and_seen_problems_to_db(
        db: Session,
        session_id: str,
        user_id: str,
        level: int,
        theme: str,
        duration_in_min: int,
        status: str,
        problems: list[tuple[str, str]]
    ) -> ContestSession:
        """
        Helper function to save contest session to the database.
        """
        try:
            # Create the main session record
            new_session = ContestSession(
                id=session_id,
                user_id=user_id,
                level=level,
                theme=theme,
                duration_in_min=duration_in_min,
                status=status,
                p1_cf_contestId=problems[0][0],
                p1_cf_index=problems[0][1],
                p2_cf_contestId=problems[1][0],
                p2_cf_index=problems[1][1],
                p3_cf_contestId=problems[2][0],
                p3_cf_index=problems[2][1],
                p4_cf_contestId=problems[3][0],
                p4_cf_index=problems[3][1]
            )

            seen_problems = [
                ContestSessionSeenProblem(
                    session_id=session_id,
                    cf_problem_contestId=contest_id,
                    cf_problem_index=index
                )
                for contest_id, index in problems
            ]

            # Add all records
            db.add(new_session)
            db.add_all(seen_problems)
            db.flush()

            return new_session

        except SQLAlchemyError as e:
            logger.exception("db.error", operation="save_contest_session_and_seen_problems_to_db", session_id=session_id, user_id=user_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_SAVING_CONTEST_SESSION
            ) from e


    @staticmethod
    def update_contest_session_problem_db_and_seen_problems_db(
        db: Session,
        session_id: str,
        problem_number: int,
        problem_contestId: str,
        problem_index: str
    ) -> ContestSession:
        """
        Update the contest session problem for one slot and add the new problem to seen.
        Keeps the old problem in seen so it is never offered again on future re-rolls.
        """
        try:
            session_row = db.query(ContestSession).filter(
                ContestSession.id == session_id
            ).first()

            setattr(session_row, f"p{problem_number}_cf_contestId", problem_contestId)
            setattr(session_row, f"p{problem_number}_cf_index", problem_index)

            # Add new problem to seen; do not remove the old one so it stays "seen"
            db.add(
                ContestSessionSeenProblem(
                    session_id=session_id,
                    cf_problem_contestId=problem_contestId,
                    cf_problem_index=problem_index
                )
            )
            db.flush()
            return session_row
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="update_contest_session_problem_db_and_seen_problems_db", session_id=session_id, problem_number=problem_number)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_WHEN_UPDATING_CONTEST_SESSION_PROBLEM
            ) from e

    @staticmethod
    def get_problem_statuses_by_id(db: Session, session_id: str) -> list[ContestSessionProblemsStatus]:
        """
        Fetch all problem status records for a session, ordered by problem_number.

        Args:
            session_id: The contest session ID

        Returns:
            List of ContestSessionProblemsStatus ordered by problem_number
        """
        try:
            problem_statuses = db.query(ContestSessionProblemsStatus).filter(
                ContestSessionProblemsStatus.session_id == session_id
            ).order_by(
                ContestSessionProblemsStatus.problem_number
            ).all()
            return problem_statuses
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_problem_statuses_by_id", session_id=session_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_PROBLEM_STATUSES
            ) from e


    @staticmethod
    def update_problem_status(
        db: Session,
        problem_status_id: int,
        state: str,
        accepted_at: str,
        solved_in_min: int
    ) -> None:
        """
        Update a single problem status record.

        Args:
            problem_status_id: The primary key of the problem status record
            state: New state (e.g. "SOLVED")
            accepted_at: Unix timestamp as string of when the submission was accepted
            solved_in_min: Time in minutes from contest start to solve
        """
        try:
            db.query(ContestSessionProblemsStatus).filter(
                ContestSessionProblemsStatus.id == problem_status_id
            ).update({
                "status": state,
                "accepted_at": accepted_at,
                "solved_in_min": solved_in_min
            })
            db.flush()
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="update_problem_status", problem_status_id=problem_status_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_UPDATING_PROBLEM_STATUS
            ) from e


    @staticmethod
    def get_last_contest_result(db: Session, user_id: str) -> ContestSessionResult | None:
        """
        Get the user's most recent contest result by joining with ContestSession.

        Args:
            user_id: The user ID

        Returns:
            The most recent ContestSessionResult or None if no previous contests
        """
        try:
            result = db.query(ContestSessionResult).join(
                ContestSession,
                ContestSessionResult.session_id == ContestSession.id
            ).filter(
                ContestSession.user_id == user_id,
                ContestSession.status == ContestStatus.FINISHED.value
            ).order_by(
                ContestSessionResult.id.desc()
            ).first()
            return result
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_last_contest_result", user_id=user_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_LAST_CONTEST_RESULT
            ) from e


    @staticmethod
    def save_contest_result(
        db: Session,
        session_id: str,
        solved_count: int,
        performance: int,
        rating_before: int,
        rating_after: int,
        rating_delta: int
    ) -> ContestSessionResult:
        """
        Save a contest result record.

        Args:
            session_id: The contest session ID
            solved_count: Number of problems solved
            performance: Calculated performance rating
            rating_before: User's rating before this contest
            rating_after: User's rating after this contest
            rating_delta: Change in rating

        Returns:
            The saved ContestSessionResult
        """
        try:
            result = ContestSessionResult(
                session_id=session_id,
                solved_count=solved_count,
                performance=performance,
                rating_before=rating_before,
                rating_after=rating_after,
                rating_delta=rating_delta
            )
            db.add(result)
            db.flush()
            return result
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="save_contest_result", session_id=session_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_SAVING_CONTEST_RESULT
            ) from e


    @staticmethod
    def end_contest_session(db: Session, session_id: str) -> None:
        """
        Update session status to FINISHED.

        Args:
            session_id: The contest session ID
        """
        try:
            db.query(ContestSession).filter(
                ContestSession.id == session_id
            ).update({
                "status": ContestStatus.FINISHED.value
            })
            db.flush()
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="end_contest_session", session_id=session_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_ENDING_CONTEST_SESSION
            ) from e


    @staticmethod
    def get_user_contest_history_paginated(
        db: Session,
        user_id: str,
        skip: int,
        limit: int
    ) -> tuple[list[tuple[ContestSession, ContestSessionResult]], int]:
        """
        Get user's finished contest sessions with results, paginated, latest first.

        Args:
            user_id: The user ID
            skip: Number of items to skip
            limit: Number of items to return

        Returns:
            Tuple of (list of (ContestSession, ContestSessionResult) tuples, total_count)
        """
        try:
            count_query = db.query(ContestSession.id).join(
                ContestSessionResult,
                ContestSession.id == ContestSessionResult.session_id
            ).filter(
                ContestSession.user_id == user_id,
                ContestSession.status == ContestStatus.FINISHED.value
            )
            total_count = count_query.count()

            rows_query = db.query(ContestSession, ContestSessionResult).join(
                ContestSessionResult,
                ContestSession.id == ContestSessionResult.session_id
            ).filter(
                ContestSession.user_id == user_id,
                ContestSession.status == ContestStatus.FINISHED.value
            ).order_by(
                ContestSessionResult.id.desc()
            ).offset(skip).limit(limit)
            rows = rows_query.all()

            return (rows, total_count)
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_user_contest_history_paginated", user_id=user_id, skip=skip, limit=limit)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_HISTORY
            ) from e


    @staticmethod
    def start_contest_session(
        db: Session,
        session_id: str,
        starts_at: int,
        ends_at: int,
        problems: list[tuple[str, str, int]]
    ) -> None:
        """
        Update session to RUNNING status and create problem status records.

        Args:
            session_id: The contest session ID
            starts_at: Unix timestamp in seconds when contest starts
            problems: List of (contestID, index, rating) tuples for each problem
        """
        try:
            # Update session status and start time
            db.query(ContestSession).filter(
                ContestSession.id == session_id
            ).update({
                "status": ContestStatus.RUNNING.value,
                "starts_at": starts_at,
                "ends_at": ends_at
            })

            # Create problem status records for all 4 problems
            for i, (contest_id, index, rating) in enumerate(problems, start=1):
                problem_status = ContestSessionProblemsStatus(
                    session_id=session_id,
                    problem_number=i,
                    problem_contestId=contest_id,
                    problem_index=index,
                    problem_rating=rating,
                    status=ProblemStatus.UNSOLVED.value,
                    accepted_at=None,
                    solved_in_min=None
                )
                db.add(problem_status)

            db.flush()
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="start_contest_session", session_id=session_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_STARTING_CONTEST_SESSION
            ) from e


    @staticmethod
    def delete_contest_session(db: Session, session_id: str) -> None:
        """
        Delete a contest session.
        """
        try:
            db.query(ContestSession).filter(
                ContestSession.id == session_id
            ).delete()
            db.flush()
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="delete_contest_session", session_id=session_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_DELETING_CONTEST_SESSION
            ) from e


    @staticmethod
    def get_user_themecp_contest_ratings_with_date(db: Session, user_id: str) -> list[tuple[str, int, int]]:
        """
        Get all finished contest sessions for the user with date, rating_after, and rating_delta.
        Returns list of (date_str, rating_after, rating_delta) ordered chronologically.
        """
        try:
            rows = (
                db.query(ContestSession, ContestSessionResult)
                .join(
                    ContestSessionResult,
                    ContestSession.id == ContestSessionResult.session_id,
                )
                .filter(
                    ContestSession.user_id == user_id,
                    ContestSession.status == ContestStatus.FINISHED.value,
                )
                .order_by(ContestSession.starts_at.asc())
                .all()
            )
            result: list[tuple[str, int, int]] = []
            for session, res in rows:
                if session.starts_at is None:
                    continue
                date_str: str = Utils.unix_timestamp_to_date_str(session.starts_at)
                result.append((date_str, res.rating_after, res.rating_delta))
            return result
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_user_themecp_contest_ratings_with_date", user_id=user_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_HISTORY
            ) from e

    @staticmethod
    def get_user_contest_attempts_by_date(db: Session, user_id: str, year: int) -> list[tuple[str, int]]:
        """
        Get count of finished contest sessions per date for the user within the given calendar year (UTC).
        Returns list of (date_str, count) ordered by date ascending.
        Only dates with at least one contest are included.
        """
        start_ts = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
        end_ts = int(datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp())
        try:
            rows = (
                db.query(ContestSession.starts_at)
                .filter(
                    ContestSession.user_id == user_id,
                    ContestSession.status == ContestStatus.FINISHED.value,
                    ContestSession.starts_at.isnot(None),
                    ContestSession.starts_at >= start_ts,
                    ContestSession.starts_at <= end_ts,
                )
                .all()
            )
            counter: Counter[str] = Counter()
            for (starts_at,) in rows:
                date_str: str = Utils.unix_timestamp_to_date_str(starts_at)
                counter[date_str] += 1
            return sorted(counter.items())
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_user_contest_attempts_by_date", user_id=user_id, year=year)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_HISTORY
            ) from e
