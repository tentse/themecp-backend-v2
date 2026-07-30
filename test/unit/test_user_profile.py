"""
Unit tests for user profile with contest stats.

Tests UserService.get_user_detail_from_token with mocked repository
to verify contest stats retrieval from Users model fields.
"""

from unittest.mock import patch, MagicMock

from api.user.user_services import UserService


class TestGetUserDetailFromTokenContestStats:
    """Tests for contest stats in get_user_detail_from_token"""

    @patch("api.user.user_services.UserRepository.get_user_by_email")
    @patch("api.user.user_services.AuthUtils.verify_token")
    def test_returns_unrated_when_no_contest_history(
        self,
        mock_verify_token: MagicMock,
        mock_get_user: MagicMock,
    ):
        """User with no contest history gets Unrated and null stats"""
        mock_verify_token.return_value = "user@example.com"
        mock_get_user.return_value = MagicMock(
            id="user-123",
            email="user@example.com",
            codeforces_handle=None,
            contest_rating=None,
            max_contest_rating=None,
            best_performance=None,
            contest_attempts=0,
        )

        result = UserService.get_user_detail_from_token(db=MagicMock(), token="fake-token")

        assert result.id == "user-123"
        assert result.email == "user@example.com"
        assert result.rating is None
        assert result.max_contest_rating is None
        assert result.best_performance is None
        assert result.contest_attempts == 0
        assert result.rating_label == "Unrated"

    @patch("api.user.user_services.UserRepository.get_user_by_email")
    @patch("api.user.user_services.AuthUtils.verify_token")
    def test_computes_stats_from_single_contest(
        self,
        mock_verify_token: MagicMock,
        mock_get_user: MagicMock,
    ):
        """Stats from single contest: last=max, best_performance, attempts=1"""
        mock_verify_token.return_value = "user@example.com"
        mock_get_user.return_value = MagicMock(
            id="user-123",
            email="user@example.com",
            codeforces_handle=None,
            contest_rating=1450,
            max_contest_rating=1450,
            best_performance=1500,
            contest_attempts=1,
        )

        result = UserService.get_user_detail_from_token(db=MagicMock(), token="fake-token")

        assert result.rating == 1450
        assert result.max_contest_rating == 1450
        assert result.best_performance == 1500
        assert result.contest_attempts == 1
        assert result.rating_label == "Specialist"

    @patch("api.user.user_services.UserRepository.get_user_by_email")
    @patch("api.user.user_services.AuthUtils.verify_token")
    def test_computes_stats_from_multiple_contests(
        self,
        mock_verify_token: MagicMock,
        mock_get_user: MagicMock,
    ):
        """Stats from multiple contests: last from most recent, max/best from all"""
        mock_verify_token.return_value = "user@example.com"
        mock_get_user.return_value = MagicMock(
            id="user-123",
            email="user@example.com",
            codeforces_handle=None,
            contest_rating=1500,
            max_contest_rating=1550,
            best_performance=1600,
            contest_attempts=3,
        )

        result = UserService.get_user_detail_from_token(db=MagicMock(), token="fake-token")

        assert result.rating == 1500
        assert result.max_contest_rating == 1550
        assert result.best_performance == 1600
        assert result.contest_attempts == 3
        assert result.rating_label == "Specialist"
