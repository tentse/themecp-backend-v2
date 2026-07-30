from sqlalchemy.orm import Session
from .contest_theme_response_models import (
    ContestThemeInput,
    ContestThemeOutput
)
from .contest_theme_repository import ContestThemeRepository

class ContestThemeService:


    @staticmethod
    def get_all_contest_themes(db: Session) -> list[ContestThemeOutput]:
        """
        Service function to get all contest themes.
        """
        contest_themes = ContestThemeRepository.get_all_contest_themes(db=db)
        return [
            ContestThemeOutput(
                id=ct.id,
                theme=ct.theme.upper()
            )
            for ct in contest_themes
        ]

    @staticmethod
    def create_contest_theme(
        db: Session,
        create_contest_theme: ContestThemeInput
    ) -> None:
        """
        Service function to create a new contest theme.
        """

        ContestThemeRepository.create_contest_theme(
            db=db,
            create_contest_theme=create_contest_theme
        )
        db.commit()

        return None
