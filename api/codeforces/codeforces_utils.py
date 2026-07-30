from datetime import datetime, timezone

import requests
from api.config import get
from fastapi import HTTPException
from api.error_constants import ErrorConstants
from .codeforces_response_model import (
    CodeforcesProblems,
    UserSubmittedProblem
)
from api.utils import Utils

class CodeforcesUtils:

    # Any problem that has this tag (e.g. Kotlin Heroes, April Fools, BOI mirrors, etc.)
    # will be skipped when selecting problems.
    _SPECIAL_TAG = "*special"

    @staticmethod
    def get_codeforces_problems() -> list[CodeforcesProblems]:
        """
        Helper function to fetch Codeforces problems.
        And format them into CodeforcesProblems model.
        """

        try:
            codeforces_problems = []
            codeforces_url = get("CODEFORCE_API_URL")
            response = requests.get(
                f"{codeforces_url}/problemset.problems",
                timeout=30
            )
            response = response.json()
            for problem in response["result"]["problems"]:
                if "rating" in problem and "tags" in problem:
                    tags = problem.get("tags", [])
                    if CodeforcesUtils._SPECIAL_TAG in tags:
                        continue
                    codeforces_problems.append(
                        CodeforcesProblems(
                            contestID=str(problem["contestId"]),
                            index=problem["index"],
                            rating=problem["rating"],
                            tags=problem["tags"]
                        )
                    )
            return codeforces_problems
        except HTTPException as e:
            raise HTTPException(status_code=503, detail=ErrorConstants.CODEFORCES_ERROR_FETCHING_PROBLEMS) from e


    @staticmethod
    def get_user_submitted_problems(codeforces_handle: str, skip: int = 1, limit: int = 1) -> list[UserSubmittedProblem]:
        """
        Helper function to fetch the set of problems solved by a user on Codeforces.
        """

        try:
            
            codeforces_url = get("CODEFORCE_API_URL")
            response = requests.get(
                f"{codeforces_url}/user.status?handle={codeforces_handle}&from={skip}&count={limit}",
                timeout=30
            )
            response = response.json()

            user_submitted_problems = []
            for submission in response["result"]:
                problem = submission.get("problem") or {}
                contest_id = problem.get("contestId")
                index = problem.get("index")
                creation_time = submission.get("creationTimeSeconds")
                if contest_id is None or index is None or creation_time is None:
                    continue
                user_submitted_problems.append(
                    UserSubmittedProblem(
                        contestID=str(contest_id),
                        index=index,
                        rating=problem.get("rating", 0),
                        verdict=submission.get("verdict", "UNKNOWN"),
                        tags=problem.get("tags", []),
                        creationTimeSeconds=creation_time
                    )
                )
    
            return user_submitted_problems
        
        except HTTPException as e:
            raise HTTPException(status_code=503, detail=ErrorConstants.CODEFORCES_ERROR_FETCHING_SOLVED_PROBLEMS) from e

    
    @staticmethod
    def get_user_attempted_problems(codeforces_handle: str) -> set[tuple[str, str]]:
        """
        Helper function to fetch the set of problems attempted by a user on Codeforces.
        """
        try:
            codeforces_url = get("CODEFORCE_API_URL")
            response = requests.get(
                f"{codeforces_url}/user.status?handle={codeforces_handle}",
                timeout=30
            )
            user_attempted_problems: set[tuple[str, str]] = set ()
            response = response.json()
            for submission in response["result"]:
                problem = submission.get("problem") or {}
                contest_id = problem.get("contestId")
                index = problem.get("index")
                if contest_id is not None and index is not None:
                    user_attempted_problems.add((str(contest_id), index))
            return user_attempted_problems
        
        except HTTPException as e:
            raise HTTPException(status_code=503, detail=ErrorConstants.CODEFORCES_ERROR_FETCHING_ATTEMPTED_PROBLEMS) from e

    @staticmethod
    def get_user_rating(codeforces_handle: str) -> int | None:
        """
        Fetch the user's current rating from Codeforces user.info API.
        Returns None if the user is unrated, or on API/network errors (so contest end does not fail on CF downtime).
        """
        try:
            codeforces_url = get("CODEFORCE_API_URL")
            response = requests.get(
                f"{codeforces_url}/user.info?handles={codeforces_handle}",
                timeout=30
            )
            response = response.json()
            if response.get("status") != "OK" or not response.get("result"):
                return None
            user = response["result"][0]
            rating = user.get("rating")
            if rating is None:
                return None
            return int(rating)
        except Exception:
            return None

    @staticmethod
    def get_user_rating_history(codeforces_handle: str) -> list[tuple[str, int, int]]:
        """
        Fetch the user's rating history from Codeforces user.rating API.
        Returns list of (date_str, rating, rating_delta) ordered chronologically.
        """
        try:
            codeforces_url = get("CODEFORCE_API_URL")
            response = requests.get(
                f"{codeforces_url}/user.rating?handle={codeforces_handle}",
                timeout=30
            )
            data = response.json()
            if data.get("status") != "OK":
                return []
            result_list = data.get("result") or []
            history: list[tuple[str, int, int]] = []
            for entry in result_list:
                ts = entry.get("ratingUpdateTimeSeconds")
                old_rating = entry.get("oldRating", 0)
                new_rating = entry.get("newRating", 0)
                if ts is None:
                    continue
                date_str = Utils.unix_timestamp_to_date_str(ts)
                rating_delta = new_rating - old_rating
                history.append((date_str, new_rating, rating_delta))
            return history
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=ErrorConstants.CODEFORCES_ERROR_FETCHING_RATING_HISTORY
            ) from e