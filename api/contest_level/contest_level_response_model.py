from pydantic import BaseModel

class ContestLevelResponse(BaseModel):
    level: int
    duration: int
    rating_1: int
    rating_2: int
    rating_3: int
    rating_4: int