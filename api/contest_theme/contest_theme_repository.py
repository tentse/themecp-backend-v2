from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from api.error_constants import ErrorConstants
from api.logging_config import get_logger
from .contest_theme_model import ContestThemes
from .contest_theme_response_models import ContestThemeInput

logger = get_logger(__name__)


class ContestThemeRepository:


    @staticmethod
    def get_all_contest_themes(db: Session) -> list[ContestThemes]:
        """
        Repository function to get all contest themes.
        """
        try:
            contest_themes = db.query(ContestThemes).all()
            return contest_themes
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="get_all_contest_themes")
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_FETCHING_CONTEST_THEMES,
            ) from e

    @staticmethod
    def create_contest_theme(
        db: Session,
        create_contest_theme: ContestThemeInput
    ) -> None:
        """
        Repository function to create a new contest theme.
        Uses a savepoint so that on duplicate (IntegrityError) we only roll back
        the failed insert, leaving any prior data in the transaction intact.
        """
        try:
            with db.begin_nested():
                new_contest_theme = ContestThemes(
                    theme=create_contest_theme.theme
                )
                db.add(new_contest_theme)
                db.flush()
            return None
        except IntegrityError as e:
            raise HTTPException(
                status_code=409,
                detail=ErrorConstants.CONTEST_THEME_ALREADY_EXISTS,
            ) from e
        except SQLAlchemyError as e:
            logger.exception("db.error", operation="create_contest_theme", theme=create_contest_theme.theme)
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.DB_ERROR_CREATING_CONTEST_THEME,
            ) from e
