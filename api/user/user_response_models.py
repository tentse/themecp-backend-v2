from pydantic import BaseModel


class UserBase(BaseModel):
    email: str | None = None
    codeforces_handle: str | None = None

class UserResponseModel(UserBase):
    id: str
    rating: int | None = None
    max_contest_rating: int | None = None
    best_performance: int | None = None
    contest_attempts: int = 0
    rating_label: str = "Unrated"

class CodeforcesHandleUpdate(BaseModel):
    codeforces_handle: str
    contestID: str
    index: str


class LeaderboardEntry(BaseModel):
    user_id: str
    codeforces_handle: str
    rating: int
    rating_label: str