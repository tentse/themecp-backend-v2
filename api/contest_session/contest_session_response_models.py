from pydantic import BaseModel, field_validator
from enum import Enum

class ContestStatus(str, Enum):
    REVIEW = "REVIEW"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"


class ProblemStatus(str, Enum):
    UNSOLVED = "UNSOLVED"
    SOLVED = "SOLVED"
    UPSOLVED = "UPSOLVED"


class ProblemDetail(BaseModel):
    contestId: str
    index: str
    rating: int
    status: ProblemStatus = ProblemStatus.UNSOLVED
    solved_in_min: int | None = None


class ContestSessionBase(BaseModel):
    level: int
    theme: str

    @field_validator("theme", mode="before")
    @classmethod
    def theme_to_lower(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

class ContestSessionOutput(ContestSessionBase):
    id: str
    status: ContestStatus
    duration_in_min: int
    user_id: str
    starts_at: int | None = None # Unix timestamp in seconds
    ends_at: int | None = None # Unix timestamp in seconds
    p1: ProblemDetail
    p2: ProblemDetail
    p3: ProblemDetail
    p4: ProblemDetail


class ContestSessionInput(ContestSessionBase):
    pass


class RefreshProblemStatusInput(BaseModel):
    problem_number: int


class ContestSessionProblemsStatus(BaseModel):
    contest_session_id: str
    starts_at: int
    ends_at: int
    p1: ProblemDetail
    p2: ProblemDetail
    p3: ProblemDetail
    p4: ProblemDetail


class CodeforcesProblems(BaseModel):
    contestId: str
    index: str
    rating: int
    tags: list[str]


class HeatgraphDataItem(BaseModel):
    date: str
    contest_attempts: int

class HeatgraphData(BaseModel):
    items: list[HeatgraphDataItem]


class ContestHistoryItem(BaseModel):
    session_id: str
    date: str  # YYYY-MM-DD from starts_at
    level: int
    theme: str
    duration_in_min: int
    performance: int
    rating: int
    rating_delta: int
    p1: ProblemDetail
    p2: ProblemDetail
    p3: ProblemDetail
    p4: ProblemDetail


class ContestHistoryOutput(BaseModel):
    items: list[ContestHistoryItem]
    skip: int
    limit: int
    total: int


class RatingPlotItem(BaseModel):
    date: str
    rating: int
    rating_delta: int


class RatingPlot(BaseModel):
    themecp_ratings: list[RatingPlotItem]
    codeforces_ratings: list[RatingPlotItem]