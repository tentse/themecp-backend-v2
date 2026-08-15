from pydantic import BaseModel
import json


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

def serialize_models(models: list[BaseModel]) -> str:
    """Convert list of Pydantic models to JSON string."""
    return json.dumps([m.model_dump() for m in models])

def deserialize_models(data: str, model_class) -> list:
    """Convert JSON string to list of Pydantic models."""
    parsed = json.loads(data)
    return [model_class.model_validate(item) for item in parsed]