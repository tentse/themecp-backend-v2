from contest_session.contest_session_response_model import (
    ContestSessionResponse
)

from api.user.user_service import (
    _validate_token_and_get_user_detail
)

from api.db.pg_database import SessionLocal

from api.contest_level.contest_level_service import (
    get_contest_level_detail
)

from api.contest_level.contest_level_response_model import (
    ContestLevelResponse
)

def create_contest_session_service(
    contest_level: int,
    contest_theme: str,
    token: str
) -> ContestSessionResponse:
    
    user_detail = _validate_token_and_get_user_detail(token)

    try:
        with SessionLocal() as db_session:
            contest_level_detail: ContestLevelResponse = get_contest_level_detail(
                db_session=db_session,
                contest_level=contest_level
            )
            
    

