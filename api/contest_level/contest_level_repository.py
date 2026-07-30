from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from api.error_constants import ErrorConstants
from api.logging_config import get_logger
from .contest_level_model import ContestLevel
from .contest_level_response_models import (
    ContestLevelInput
)

logger = get_logger(__name__)


class ContestLevelRepository:


    @staticmethod
    def get_contest_level_detail_by_level(db: Session, level: int) -> ContestLevel:
        """
        Helper functoin to fetch contest level detail by
        level
        """
        try:
            contest_level_detail = db.query(ContestLevel).filter(
                ContestLevel.level == level
            ).first()
            return contest_level_detail
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_contest_level_detail_by_level", level=level)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_LEVEL
            ) from e

    @staticmethod
    def get_all_contest_levels(db: Session) -> list[ContestLevel]:
        """
        Fetch all contest levels ordered by level ascending.
        """
        try:
            contest_levels = db.query(ContestLevel).order_by(ContestLevel.level.asc()).all()
            return contest_levels
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_all_contest_levels")
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_LEVEL
            ) from e

    @staticmethod
    def create_new_contest_level(db: Session, create_contest_level: ContestLevelInput) -> ContestLevel:
        """
        Contest level creator function
        """
        try:
            contest_level = ContestLevel(
                level=create_contest_level.level,
                duration_in_min=create_contest_level.duration_in_min,
                performance=create_contest_level.performance,
                p1_rating=create_contest_level.p1_rating,
                p2_rating=create_contest_level.p2_rating,
                p3_rating=create_contest_level.p3_rating,
                p4_rating=create_contest_level.p4_rating
            )

            db.add(contest_level)
            db.flush()
            return contest_level
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="create_new_contest_level", level=create_contest_level.level)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_CREATING_CONTEST_LEVEL
            ) from e
