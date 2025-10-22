from pydantic import BaseModel
from typing import Optional

class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    codeforces_handle: Optional[str] = None