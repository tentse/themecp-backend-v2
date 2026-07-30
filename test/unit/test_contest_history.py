"""
Unit tests for contest history feature.

Tests:
- Utils.unix_timestamp_to_date_str converter
- ContestSessionService.get_contest_history_service (with mocked repository)
"""

import pytest
from unittest.mock import patch, MagicMock

from api.utils import Utils
from api.contest_session.contest_session_services import ContestSessionService


class TestUnixTimestampToDateStr:
    """Tests for Utils.unix_timestamp_to_date_str"""

    def test_converts_to_yyyy_mm_dd(self):
        """Unix timestamp 1708123456 = 2024-02-16 in UTC"""
        result = Utils.unix_timestamp_to_date_str(1708123456)
        assert result == "2024-02-16"

    def test_midnight_utc(self):
        """Unix timestamp for 2020-01-01 00:00:00 UTC = 1577836800"""
        result = Utils.unix_timestamp_to_date_str(1577836800)
        assert result == "2020-01-01"

    def test_end_of_day_utc(self):
        """Unix timestamp for 2023-12-31 23:59:59 UTC"""
        result = Utils.unix_timestamp_to_date_str(1704067199)
        assert result == "2023-12-31"


class TestGetContestHistoryService:
    """Tests for ContestSessionService.get_contest_history_service with mocked repository"""

    @patch("api.contest_session.contest_session_services.ContestSessionRepository.get_user_contest_history_paginated")
    @patch("api.contest_session.contest_session_services.UserService.get_user_detail_from_token")
    @patch("api.contest_session.contest_session_services.ContestLevelService.get_problem_level_ratings")
    def test_returns_skip_limit_total(
        self,
        mock_get_ratings,
        mock_get_user,
        mock_get_history,
    ):
        """Response includes skip, limit, total"""
        mock_get_user.return_value = MagicMock(id="user-123")
        mock_get_ratings.return_value = MagicMock(
            p1_rating=1000, p2_rating=1200, p3_rating=1400, p4_rating=1600
        )
        mock_get_history.return_value = ([], 0)

        result = ContestSessionService.get_contest_history(
            db=MagicMock(),
            token="fake-token",
            skip=10,
            limit=5,
        )

        assert result.skip == 10
        assert result.limit == 5
        assert result.total == 0
        assert result.items == []

    @patch("api.contest_session.contest_session_services.ContestSessionRepository.get_problem_statuses_by_id")
    @patch("api.contest_session.contest_session_services.ContestSessionRepository.get_user_contest_history_paginated")
    @patch("api.contest_session.contest_session_services.UserService.get_user_detail_from_token")
    @patch("api.contest_session.contest_session_services.ContestLevelService.get_problem_level_ratings")
    def test_maps_repository_rows_to_items(
        self,
        mock_get_ratings,
        mock_get_user,
        mock_get_history,
        mock_get_problem_statuses,
    ):
        """Repository rows are mapped to ContestHistoryItem with date from starts_at"""
        mock_get_user.return_value = MagicMock(id="user-123")
        contest_level = MagicMock(
            p1_rating=1000, p2_rating=1200, p3_rating=1400, p4_rating=1600
        )
        mock_get_ratings.return_value = contest_level

        session = MagicMock()
        session.id = "session-1"
        session.level = 21
        session.theme = "greedy"
        session.duration_in_min = 120
        session.starts_at = 1708123456
        session.p1_cf_contestId = "5000"
        session.p1_cf_index = "A"
        session.p2_cf_contestId = "5000"
        session.p2_cf_index = "B"
        session.p3_cf_contestId = "5000"
        session.p3_cf_index = "C"
        session.p4_cf_contestId = "5000"
        session.p4_cf_index = "D"

        result_row = MagicMock()
        result_row.solved_count = 2
        result_row.performance = 1500
        result_row.rating_before = 1400
        result_row.rating_after = 1450
        result_row.rating_delta = 50

        mock_get_history.return_value = ([(session, result_row)], 1)

        # Mock problem statuses: p1 and p2 SOLVED (with solved_in_min), p3 and p4 UNSOLVED
        problem_statuses = [
            MagicMock(problem_number=1, status="SOLVED", solved_in_min=10),
            MagicMock(problem_number=2, status="SOLVED", solved_in_min=25),
            MagicMock(problem_number=3, status="UNSOLVED", solved_in_min=None),
            MagicMock(problem_number=4, status="UNSOLVED", solved_in_min=None),
        ]
        mock_get_problem_statuses.return_value = problem_statuses

        response = ContestSessionService.get_contest_history(
            db=MagicMock(),
            token="fake-token",
            skip=0,
            limit=10,
        )

        assert len(response.items) == 1
        item = response.items[0]
        assert item.date == "2024-02-16"
        assert item.level == 21
        assert item.theme == "greedy"
        assert item.performance == 1500
        assert item.rating == 1450
        assert item.rating_delta == 50
        assert item.p1_status.value == "SOLVED"
        assert item.p2_status.value == "SOLVED"
        assert item.p3_status.value == "UNSOLVED"
        assert item.p4_status.value == "UNSOLVED"
        assert item.p1_solved_in_min == 10
        assert item.p2_solved_in_min == 25
        assert item.p3_solved_in_min is None
        assert item.p4_solved_in_min is None
        assert response.total == 1

    @patch("api.contest_session.contest_session_services.ContestSessionRepository.get_problem_statuses_by_id")
    @patch("api.contest_session.contest_session_services.ContestSessionRepository.get_user_contest_history_paginated")
    @patch("api.contest_session.contest_session_services.UserService.get_user_detail_from_token")
    @patch("api.contest_session.contest_session_services.ContestLevelService.get_problem_level_ratings")
    def test_solved_in_min_none_when_unsolved(
        self,
        mock_get_ratings,
        mock_get_user,
        mock_get_history,
        mock_get_problem_statuses,
    ):
        """solved_in_min is None in response when status is UNSOLVED even if DB has a value"""
        mock_get_user.return_value = MagicMock(id="user-123")
        mock_get_ratings.return_value = MagicMock(
            p1_rating=1000, p2_rating=1200, p3_rating=1400, p4_rating=1600
        )

        session = MagicMock()
        session.id = "session-1"
        session.level = 21
        session.theme = "greedy"
        session.duration_in_min = 120
        session.starts_at = 1708123456
        session.p1_cf_contestId = "5000"
        session.p1_cf_index = "A"
        session.p2_cf_contestId = "5000"
        session.p2_cf_index = "B"
        session.p3_cf_contestId = "5000"
        session.p3_cf_index = "C"
        session.p4_cf_contestId = "5000"
        session.p4_cf_index = "D"

        result_row = MagicMock()
        result_row.performance = 1500
        result_row.rating_after = 1450
        result_row.rating_delta = 50

        mock_get_history.return_value = ([(session, result_row)], 1)

        # p1 UNSOLVED but DB has solved_in_min=99 (should not be exposed)
        problem_statuses = [
            MagicMock(problem_number=1, status="UNSOLVED", solved_in_min=99),
            MagicMock(problem_number=2, status="UNSOLVED", solved_in_min=None),
            MagicMock(problem_number=3, status="UNSOLVED", solved_in_min=None),
            MagicMock(problem_number=4, status="UNSOLVED", solved_in_min=None),
        ]
        mock_get_problem_statuses.return_value = problem_statuses

        response = ContestSessionService.get_contest_history(
            db=MagicMock(),
            token="fake-token",
            skip=0,
            limit=10,
        )

        assert len(response.items) == 1
        item = response.items[0]
        assert item.p1_status.value == "UNSOLVED"
        assert item.p1_solved_in_min is None
        assert item.p2_solved_in_min is None
        assert item.p3_solved_in_min is None
        assert item.p4_solved_in_min is None
