from api.contest_level.contest_level_response_model import (
    ContestLevelResponse
)
from api.contest_level.contest_level_repository import (
    get_contest_level_repository
)

import logging
from fastapi import HTTPException
from starlette import status
from api.error_constants import ErrorConstants
logger = logging.getLogger(__name__)

def get_contest_level_service(contest_level: int) -> ContestLevelResponse:
    try:
        contest_level_detail = get_contest_level_repository(contest_level=contest_level)

        return ContestLevelResponse(
            level = contest_level_detail.level,
            duration = contest_level_detail.duration,
            rating_1 = contest_level_detail.rating_1,
            rating_2 = contest_level_detail.rating_2,
            rating_3 = contest_level_detail.rating_3,
            rating_4 = contest_level_detail.rating_4,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Failed to get contest level with error: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorConstants.DATABASE_ERROR)