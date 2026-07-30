from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.db.pg_database import get_db
from .contest_level_services import ContestLevelService
from .contest_level_response_models import ContestLevelOutput

DbSession = Annotated[Session, Depends(get_db)]

contest_level_router = APIRouter(
    prefix="/contest-level",
    tags=["Contest Level"],
)


@contest_level_router.get("", status_code=200)
def get_all_contest_levels(db: DbSession) -> list[ContestLevelOutput]:
    """
    Get all contest levels ordered by level ascending.
    """
    return ContestLevelService.get_all_contest_levels(db=db)
