"""
Unit tests for numeric configuration reading.

These settings are read at import time, so a bad value must not raise — it would
stop the service booting. Every path falls back to the documented default.
"""

import pytest

from api.config import DEFAULTS, get_int


LEADERBOARD_KEYS = [
    "LEADERBOARD_DEFAULT_LIMIT",
    "LEADERBOARD_MAX_LIMIT",
    "LEADERBOARD_MIN_CONTESTS",
    "LEADERBOARD_ACTIVE_WITHIN_DAYS",
]


class TestGetInt:
    """Tests for config.get_int"""

    @pytest.mark.parametrize("key", LEADERBOARD_KEYS)
    def test_falls_back_to_default_when_unset(self, key, monkeypatch):
        """With nothing in the environment, the documented default is used."""
        monkeypatch.delenv(key, raising=False)

        assert get_int(key) == int(DEFAULTS[key])

    @pytest.mark.parametrize("key", LEADERBOARD_KEYS)
    def test_environment_value_wins(self, key, monkeypatch):
        monkeypatch.setenv(key, "42")

        assert get_int(key) == 42

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_value_falls_back(self, blank, monkeypatch):
        """
        Railway stores an emptied variable as an empty string rather than
        removing it, so blank has to mean "not configured".
        """
        monkeypatch.setenv("LEADERBOARD_MIN_CONTESTS", blank)

        assert get_int("LEADERBOARD_MIN_CONTESTS") == int(
            DEFAULTS["LEADERBOARD_MIN_CONTESTS"]
        )

    @pytest.mark.parametrize("garbage", ["ten", "10.5", '"10"', "10 contests"])
    def test_non_numeric_value_falls_back_instead_of_raising(self, garbage, monkeypatch):
        """
        A quoted or mistyped value must not crash the import. Quoting in
        particular is easy to do by accident — the same mistake previously broke
        CORS in production.
        """
        monkeypatch.setenv("LEADERBOARD_DEFAULT_LIMIT", garbage)

        assert get_int("LEADERBOARD_DEFAULT_LIMIT") == int(
            DEFAULTS["LEADERBOARD_DEFAULT_LIMIT"]
        )

    def test_surrounding_whitespace_is_tolerated(self, monkeypatch):
        monkeypatch.setenv("LEADERBOARD_MAX_LIMIT", "  50  ")

        assert get_int("LEADERBOARD_MAX_LIMIT") == 50

    def test_every_leaderboard_default_is_an_integer(self):
        """
        The fallback path does int(DEFAULTS[key]), so a non-numeric default here
        would only fail once the variable was unset in production.
        """
        for key in LEADERBOARD_KEYS:
            assert isinstance(int(DEFAULTS[key]), int)
