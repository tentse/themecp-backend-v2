"""
Unit tests for caching in UserService.get_user_profile.

The cache functions are patched rather than driven through a real Redis, so
these assert the caching *logic*: a miss falls through to the database and
writes back, a hit skips the database entirely, and two viewers of the same
profile never share an entry.

That the value genuinely lands in Redis is covered separately by
test/integration/test_user_profile_cache.py.
"""

from unittest.mock import MagicMock, patch

from api.user.user_response_models import UserResponseModel
from api.user.user_services import UserService

# Matches the ttl passed by get_user_profile. Kept as a constant so the test
# fails loudly if the service starts caching for a different duration.
CACHE_TTL_SECONDS = 60


def make_user_row(**overrides) -> MagicMock:
    """Stand-in for the Users row that resolve_profile_user returns."""
    fields = {
        "id": "user-123",
        "email": "owner@example.com",
        "codeforces_handle": "tourist",
        "contest_rating": 1450,
        "max_contest_rating": 1500,
        "best_performance": 1600,
        "contest_attempts": 3,
    }
    fields.update(overrides)
    return MagicMock(**fields)


def make_cached_profile(**overrides) -> UserResponseModel:
    """A response model matching make_user_row, for priming the cache."""
    fields = {
        "id": "user-123",
        "email": "owner@example.com",
        "codeforces_handle": "tourist",
        "rating": 1450,
        "max_contest_rating": 1500,
        "best_performance": 1600,
        "contest_attempts": 3,
        "rating_label": "Specialist",
    }
    fields.update(overrides)
    return UserResponseModel(**fields)


class TestGetUserProfileCacheWrite:
    """The miss path: read through to the database, then populate the cache."""

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_a_miss_stores_the_response_with_a_ttl(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """A miss writes the serialized response back under a "user:" key."""
        mock_cache_get.return_value = None
        mock_resolve.return_value = (make_user_row(), True)

        result = UserService.get_user_profile(
            db=MagicMock(), token="jwt-token", user_id="user-123"
        )

        mock_cache_set.assert_called_once()
        key, payload = mock_cache_set.call_args.args

        assert key.startswith("user:")
        assert mock_cache_set.call_args.kwargs["ttl"] == CACHE_TTL_SECONDS
        # What was stored has to rebuild exactly what the caller was handed,
        # or the second request returns something different from the first.
        assert UserResponseModel.model_validate_json(payload) == result

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_the_cache_is_read_before_the_database(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """The lookup key is the first thing computed, before any query runs."""
        mock_cache_get.return_value = None
        mock_resolve.return_value = (make_user_row(), True)

        UserService.get_user_profile(
            db=MagicMock(), token="jwt-token", user_id="user-123"
        )

        mock_cache_get.assert_called_once()
        read_key = mock_cache_get.call_args.args[0]
        written_key = mock_cache_set.call_args.args[0]
        # The key read on a miss must be the key written after it, or every
        # request is a miss and the cache never serves anything.
        assert read_key == written_key


class TestGetUserProfileCacheRead:
    """The hit path: serve from the cache without querying anything."""

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_a_hit_is_served_without_touching_the_database(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """A cached entry short-circuits the query and is not rewritten."""
        cached = make_cached_profile()
        mock_cache_get.return_value = cached.model_dump_json()

        result = UserService.get_user_profile(
            db=MagicMock(), token="jwt-token", user_id="user-123"
        )

        assert result == cached
        mock_resolve.assert_not_called()
        # Rewriting on every hit would slide the TTL forward indefinitely and
        # the entry would never refresh from the database.
        mock_cache_set.assert_not_called()

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_unreadable_cached_json_falls_back_to_the_database(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """
        A corrupt entry — or one written by an older, incompatible version of
        the response model — must degrade to a miss rather than raise.
        """
        mock_cache_get.return_value = "not-json-at-all"
        mock_resolve.return_value = (make_user_row(), True)

        result = UserService.get_user_profile(
            db=MagicMock(), token="jwt-token", user_id="user-123"
        )

        assert result.id == "user-123"
        mock_resolve.assert_called_once()
        # The bad entry is overwritten with a readable one.
        mock_cache_set.assert_called_once()


class TestGetUserProfileCacheKeyIsolation:
    """Who is asking, and about whom, both have to be part of the key."""

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_owner_and_stranger_do_not_share_an_entry(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """
        The owner's copy carries their email address and a stranger's does not.
        A shared key would serve one user's email to another.
        """
        mock_cache_get.return_value = None

        mock_resolve.return_value = (make_user_row(), True)
        UserService.get_user_profile(
            db=MagicMock(), token="owner-token", user_id="user-123"
        )

        mock_resolve.return_value = (make_user_row(), False)
        UserService.get_user_profile(
            db=MagicMock(), token="stranger-token", user_id="user-123"
        )

        owner_key = mock_cache_get.call_args_list[0].args[0]
        stranger_key = mock_cache_get.call_args_list[1].args[0]
        assert owner_key != stranger_key

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_different_profiles_do_not_share_an_entry(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """One viewer looking at two different profiles gets two entries."""
        mock_cache_get.return_value = None
        mock_resolve.return_value = (make_user_row(), False)

        UserService.get_user_profile(
            db=MagicMock(), token="viewer-token", user_id="user-aaa"
        )
        UserService.get_user_profile(
            db=MagicMock(), token="viewer-token", user_id="user-bbb"
        )

        first_key = mock_cache_get.call_args_list[0].args[0]
        second_key = mock_cache_get.call_args_list[1].args[0]
        assert first_key != second_key


class TestGetUserProfileCacheKeyWithOptionalInputs:
    """
    Both inputs to the cache key are optional in normal use: viewing your own
    profile sends no user_id, and viewing someone else's while logged out sends
    no token. Neither may break the key.
    """

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_own_profile_without_a_user_id_is_cached(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """GET /users with only a bearer token — the logged-in default."""
        mock_cache_get.return_value = None
        mock_resolve.return_value = (make_user_row(), True)

        result = UserService.get_user_profile(
            db=MagicMock(), token="jwt-token", user_id=None
        )

        assert result.id == "user-123"
        mock_cache_set.assert_called_once()

    @patch("api.user.user_services.set")
    @patch("api.user.user_services.get")
    @patch("api.user.user_services.UserService.resolve_profile_user")
    def test_anonymous_view_without_a_token_is_cached(
        self,
        mock_resolve: MagicMock,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ):
        """GET /users?user_id=... with no Authorization header."""
        mock_cache_get.return_value = None
        mock_resolve.return_value = (make_user_row(email=None), False)

        result = UserService.get_user_profile(
            db=MagicMock(), token=None, user_id="user-123"
        )

        assert result.id == "user-123"
        mock_cache_set.assert_called_once()
