import structlog
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .user_response_models import (
    UserResponseModel,
    CodeforcesHandleUpdate
)
from api.codeforces.codeforces_response_model import (
    CodeforcesProblems
)
from .user_repository import UserRepository
from .rating_utils import get_rating_label
from api.auth.auth_utils import AuthUtils
from api.codeforces.codeforces_utils import CodeforcesUtils, UserSubmittedProblem
from api.error_constants import ErrorConstants


class UserService:


    @staticmethod
    def get_user_detail_from_token(db: Session, token: str) -> UserResponseModel:
        """
        Retrieve user details based on the provided token.
        """
        email: str = AuthUtils.verify_token(token=token)

        user_data = UserRepository.get_user_by_email(db=db, email=email)

        structlog.contextvars.bind_contextvars(user_id=user_data.id)

        last_contest_rating: int | None = user_data.contest_rating
        max_contest_rating: int | None = user_data.max_contest_rating
        best_performance: int | None = user_data.best_performance
        contest_attempts: int = user_data.contest_attempts or 0

        return UserResponseModel(
            id=user_data.id,
            email=user_data.email,
            codeforces_handle=user_data.codeforces_handle,
            rating=last_contest_rating,
            max_contest_rating=max_contest_rating,
            best_performance=best_performance,
            contest_attempts=contest_attempts,
            rating_label=get_rating_label(last_contest_rating),
        )


    @staticmethod
    def get_user_by_email_service(db: Session, email: str) -> UserResponseModel:
        """
        Service function to get user details by email.
        """

        user_data = UserRepository.get_user_by_email(db=db, email=email)

        return UserResponseModel(
            id=user_data.id,
            email=user_data.email,
            codeforces_handle=user_data.codeforces_handle
        )


    @staticmethod
    def register_user_service(db: Session, email: str) -> None:
        """
        Service function to register a new user.
        """
        UserRepository.check_user_exists(db=db, email=email)

        UserRepository.register_user_repository(db=db, email=email)
        db.commit()


    @staticmethod
    def get_codeforces_problem_for_handle_verification(db: Session, codeforces_handle: str, token: str) -> CodeforcesProblems:
        """
        Service function to get a Codeforces problem URL for handle verification.
        """

        UserService.get_user_detail_from_token(db=db, token=token)

        user_submitted_problems: list[UserSubmittedProblem] = CodeforcesUtils.get_user_submitted_problems(codeforces_handle=codeforces_handle)

        if not user_submitted_problems:
            raise HTTPException(
                status_code=404,
                detail=ErrorConstants.UNSOLVED_PROBLEM_NOT_FOUND
            )

        user_last_submitted_problem: UserSubmittedProblem = user_submitted_problems[0]

        codeforces_problems: list[CodeforcesProblems] = CodeforcesUtils.get_codeforces_problems()

        selected_problem: CodeforcesProblems = None
        for problem in codeforces_problems:
            if problem.contestID != user_last_submitted_problem.contestID and problem.index != user_last_submitted_problem.index:
                selected_problem: CodeforcesProblems = problem
                break

        return selected_problem


    @staticmethod
    def update_codeforces_handle(db: Session, token: str, codeforces_handle_verification: CodeforcesHandleUpdate) -> bool:

        """
        Service function to update the Codeforces handle for a user after verification.
        """

        user_detail: UserResponseModel = UserService.get_user_detail_from_token(db=db, token=token)

        user_submitted_problems: list[UserSubmittedProblem] = CodeforcesUtils.get_user_submitted_problems(
            codeforces_handle=codeforces_handle_verification.codeforces_handle,
            skip=1,
            limit=1
        )

        if not user_submitted_problems:
            raise HTTPException(
                status_code=404,
                detail=ErrorConstants.UNSOLVED_PROBLEM_NOT_FOUND
            )

        user_last_submitted_problem: UserSubmittedProblem = user_submitted_problems[0]

        if (user_last_submitted_problem.contestID == codeforces_handle_verification.contestID and user_last_submitted_problem.index == codeforces_handle_verification.index) and user_last_submitted_problem.verdict == "COMPILATION_ERROR":

            UserRepository.update_codeforces_handle_repository(
                db=db,
                email=user_detail.email,
                codeforces_handle=codeforces_handle_verification.codeforces_handle
            )
            db.commit()
            return True

        return False
