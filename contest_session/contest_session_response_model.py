from pydantic import BaseModel
from typing import Optional, List

class ContestSessionResponse(BaseModel):
    id: str
    user_id: str
    contest_level: int
    contest_theme: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: int
    rating_1: int
    rating_2: int
    rating_3: int
    rating_4: int
    t1 = Optional[str] = None
    t2 = Optional[str] = None
    t3 = Optional[str] = None
    t4 = Optional[str] = None
    problem_1_id: str
    problem_2_id: str
    problem_3_id: str
    problem_4_id: str
    problem_1_index: str
    problem_2_index: str
    problem_3_index: str
    problem_4_index: str
    status: str
    

