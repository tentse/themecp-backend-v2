from pydantic import BaseModel

class ContestLevelBase(BaseModel):
    level: int
    duration_in_min: int
    performance: int
    p1_rating: int
    p2_rating: int
    p3_rating: int
    p4_rating: int


class ContestLevelInput(ContestLevelBase):
    pass


class ContestLevelOutput(ContestLevelBase):
    id: int