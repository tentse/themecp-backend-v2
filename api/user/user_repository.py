import time

from .user_model import Users
from sqlalchemy import exists
from sqlalchemy.orm import Session
from api.utils import Utils
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from api.error_constants import ErrorConstants
from api.logging_config import get_logger
from api.contest_session.contest_session_models import ContestSession
from api.contest_session.contest_session_response_models import ContestStatus

logger = get_logger(__name__)

SECONDS_PER_DAY = 86_400


class UserRepository:


    @staticmethod
    def register_user_repository(db: Session, email: str) -> Users:
        """
        Repository function to register a new user.
        """

        try:
            new_user = Users(
                id=Utils.generate_id(),
                email=email,
                contest_attempts=0
            )

            db.add(new_user)
            db.flush()
            return new_user
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="register_user_repository", email=email)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_REGISTERING_USER
            ) from e


    @staticmethod
    def check_user_exists(db: Session, email: str):
        """
        Repository function to check if a user exists by email.
        """

        try:
            user = db.query(Users).filter(Users.email == email).first()

            if user is not None:
                raise HTTPException(
                    status_code=409,
                    detail=ErrorConstants.USER_ALREADY_EXISTS
                )

        except SQLAlchemyError as e:
            logger.exception("db.error", operation="check_user_exists", email=email)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_CHECKING_USER_EXISTENCE
            ) from e


    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Users:
        """
        Repository function to get user details by email.
        """

        try:
            user: Users = db.query(Users).filter(Users.email == email).first()

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail=ErrorConstants.UNAUTHORIZED
                )

            return user
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_user_by_email", email=email)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_USER
            ) from e

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Users:
        """
        Repository function to get user details by user id.
        """

        try:
            user = db.query(Users).filter(Users.id == user_id).first()

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorConstants.USER_NOT_FOUND
                )

            return user
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_user_by_id", user_id=user_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_USER
            ) from e


    @staticmethod
    def codeforces_handle_exists(
        db: Session,
        codeforces_handle: str
    ) -> bool:
        """
        Repository function to check if codeforces handle already added or not
        """
        try:
            existing_codeforces_handle_user = db.query(Users).filter(
                Users.codeforces_handle == codeforces_handle,
            ).first()
            if existing_codeforces_handle_user:
                raise HTTPException(
                    status_code=409,
                    detail=ErrorConstants.CODEFORCES_HANDLE_ALREADY_EXISTS
                )
            return False
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="codeforces_handle_exists", codeforces_handle=codeforces_handle)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_UPDATING_CODEFORCES_HANDLE
            ) from e


    @staticmethod
    def update_codeforces_handle_repository(
        db: Session,
        email: str,
        codeforces_handle: str
    ) -> Users:
        """
        Repository function to update the Codeforces handle for a user.
        """

        try:
            user: Users = db.query(Users).filter(Users.email == email).first()

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorConstants.USER_NOT_FOUND
                )
            elif user.codeforces_handle:
                raise HTTPException(
                    status_code=409,
                    detail=ErrorConstants.CODEFORCES_HANDLE_ALREADY_ADDED
                )

            UserRepository.codeforces_handle_exists(db=db, codeforces_handle=codeforces_handle)

            user.codeforces_handle = codeforces_handle
            db.flush()
            return user
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="update_codeforces_handle_repository", email=email, codeforces_handle=codeforces_handle)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_UPDATING_CODEFORCES_HANDLE
            ) from e

    @staticmethod
    def get_top_rated_users(
        db: Session,
        limit: int,
        min_contests: int = 0,
        active_within_days: int | None = None
    ) -> list[Users]:
        """
        Repository function to fetch the highest-rated users for the leaderboard.

        A user is ranked only if they have a Codeforces handle, a rating, at least
        `min_contests` finished contests, and — when `active_within_days` is set —
        at least one finished contest inside that window.

        Recency is written as EXISTS rather than MAX(starts_at) so the query can
        stop at a user's first recent contest instead of aggregating all of them;
        `ix_contest_session_user_id_status_starts_at` covers exactly that lookup.
        """
        try:
            query = (
                db.query(Users)
                .filter(
                    Users.codeforces_handle.isnot(None),
                    Users.contest_rating.isnot(None),
                    Users.contest_attempts >= min_contests
                )
            )

            if active_within_days is not None:
                cutoff = int(time.time()) - active_within_days * SECONDS_PER_DAY
                query = query.filter(
                    exists().where(
                        ContestSession.user_id == Users.id,
                        ContestSession.status == ContestStatus.FINISHED.value,
                        ContestSession.starts_at >= cutoff
                    )
                )

            return (
                query
                .order_by(Users.contest_rating.desc(), Users.codeforces_handle.asc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_top_rated_users", limit=limit)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_LEADERBOARD
            ) from e


    @staticmethod
    def update_user_contest_stats(
        db: Session,
        user_id: str,
        contest_rating: int,
        max_contest_rating: int,
        best_performance: int,
        contest_attempts: int
    ) -> None:
        """
        Repository function to update contest stats for a user.
        """
        try:
            user: Users = db.query(Users).filter(Users.id == user_id).first()

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorConstants.USER_NOT_FOUND
                )

            user.contest_rating = contest_rating
            user.max_contest_rating = max_contest_rating
            user.best_performance = best_performance
            user.contest_attempts = contest_attempts
            db.flush()
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="update_user_contest_stats", user_id=user_id)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_USER
            ) from e
