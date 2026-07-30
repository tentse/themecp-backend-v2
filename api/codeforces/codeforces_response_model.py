from pydantic import BaseModel


class CodeforcesProblems(BaseModel):
    contestID: str
    index: str
    rating: int
    tags: list[str]


class UserSubmittedProblem(CodeforcesProblems):
    verdict: str
    creationTimeSeconds: int