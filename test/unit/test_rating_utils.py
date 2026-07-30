"""
Unit tests for rating_utils.get_rating_label.

Tests Codeforces-style rating label mapping for all rating ranges.
"""

import pytest

from api.user.rating_utils import get_rating_label


class TestGetRatingLabel:
    """Tests for get_rating_label function"""

    def test_unrated_returns_unrated(self):
        """None rating returns Unrated"""
        assert get_rating_label(None) == "Unrated"

    @pytest.mark.parametrize("rating", [0, 800, 1199])
    def test_newbie_range(self, rating: int):
        """Rating 0-1199 returns Newbie"""
        assert get_rating_label(rating) == "Newbie"

    @pytest.mark.parametrize("rating", [1200, 1299, 1399])
    def test_pupil_range(self, rating: int):
        """Rating 1200-1399 returns Pupil"""
        assert get_rating_label(rating) == "Pupil"

    @pytest.mark.parametrize("rating", [1400, 1499, 1599])
    def test_specialist_range(self, rating: int):
        """Rating 1400-1599 returns Specialist"""
        assert get_rating_label(rating) == "Specialist"

    @pytest.mark.parametrize("rating", [1600, 1799, 1899])
    def test_expert_range(self, rating: int):
        """Rating 1600-1899 returns Expert"""
        assert get_rating_label(rating) == "Expert"

    @pytest.mark.parametrize("rating", [1900, 1999, 2099])
    def test_candidate_master_range(self, rating: int):
        """Rating 1900-2099 returns Candidate Master"""
        assert get_rating_label(rating) == "Candidate Master"

    @pytest.mark.parametrize("rating", [2100, 2199, 2299])
    def test_master_range(self, rating: int):
        """Rating 2100-2299 returns Master"""
        assert get_rating_label(rating) == "Master"

    @pytest.mark.parametrize("rating", [2300, 2350, 2399])
    def test_international_master_range(self, rating: int):
        """Rating 2300-2399 returns International Master"""
        assert get_rating_label(rating) == "International Master"

    @pytest.mark.parametrize("rating", [2400, 2499, 2599])
    def test_grandmaster_range(self, rating: int):
        """Rating 2400-2599 returns Grandmaster"""
        assert get_rating_label(rating) == "Grandmaster"

    @pytest.mark.parametrize("rating", [2600, 2799, 2999])
    def test_international_grandmaster_range(self, rating: int):
        """Rating 2600-2999 returns International Grandmaster"""
        assert get_rating_label(rating) == "International Grandmaster"

    @pytest.mark.parametrize("rating", [3000, 3500, 4000])
    def test_legendary_grandmaster_range(self, rating: int):
        """Rating >= 3000 returns Legendary Grandmaster"""
        assert get_rating_label(rating) == "Legendary Grandmaster"
