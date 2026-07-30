from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.db.pg_database import get_db
from api.admin import require_admin

from .contest_theme_response_models import (
    ContestThemeInput,
    ContestThemeOutput
)
from .contest_theme_services import ContestThemeService

DbSession = Annotated[Session, Depends(get_db)]

contest_theme_router = APIRouter(
    prefix="/contest-theme",
    tags=["Contest Theme"]
)


@contest_theme_router.get("", status_code=200)
def get_all_contest_themes(db: DbSession) -> list[ContestThemeOutput]:
    """
    Get all contest themes.
    """
    return ContestThemeService.get_all_contest_themes(db=db)

@contest_theme_router.post(
    "",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def create_contest_theme(
    create_contest_theme: ContestThemeInput,
    db: DbSession,
) -> None:
    """
    Create a new contest theme.

    Requires the `ADMIN_API_TOKEN` bearer token.
    """
    ContestThemeService.create_contest_theme(
        db=db,
        create_contest_theme=create_contest_theme
    )
