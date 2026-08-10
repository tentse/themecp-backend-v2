"""
Unit tests for contest history feature.

Tests:
- Utils.unix_timestamp_to_date_str converter

The former TestGetContestHistoryService class was removed. It patched
ContestSessionRepository.get_problem_statuses_by_id and
ContestLevelService.get_problem_level_ratings, so it asserted the internal call
structure of get_contest_history rather than its behaviour, and those per-row
calls no longer exist. The same behaviour is covered end to end, against a real
database, by TestGetContestHistory in
test/integration/test_contest_session.py.
"""

from api.utils import Utils


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
