from unittest.mock import patch

from api.cache.redis_client import client as cache_client
from api.config import get_int
from api.user.user_repository import UserRepository
from api.user.user_response_models import (
    LeaderboardEntry,
    UserResponseModel,
    deserialize_models,
)

USER_PROFILE_CACHE_TTL_SECONDS = 60
LEADERBOARD_CACHE_TTL_SECONDS = 120


def get_cached(cache_key: str) -> str | None:
    """The raw JSON cached for this viewer, or None if there is no entry."""
    return cache_client.get(cache_key)


class TestUserProfileCacheInRedis:

    def test_request_populates_redis_with_an_expiring_key(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]

        cache_key = f"user:{user_id}:{token}"

        assert get_cached(cache_key) is None

        response = api_client.get(
            f"/users?user_id={user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        assert get_cached(cache_key) is not None

        ttl = cache_client.ttl(cache_key)
        assert 0 < ttl <= USER_PROFILE_CACHE_TTL_SECONDS

    def test_the_cached_payload_rebuilds_the_response_body(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]

        response = api_client.get(
            f"/users?user_id={user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        cache_key = f"user:{user_id}:{token}"

        stored = get_cached(cache_key)
        assert stored is not None, "nothing was written to the cache"
        assert UserResponseModel.model_validate_json(stored).model_dump() == response.json()

    def test_a_second_request_returns_the_same_body(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        first = api_client.get(f"/users?user_id={user_id}", headers=headers)
        second = api_client.get(f"/users?user_id={user_id}", headers=headers)

        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()

        cache_key = f"user:{user_id}:{token}"
        stored = get_cached(cache_key)

        assert UserResponseModel.model_validate_json(stored).model_dump() == second.json()

    def test_a_second_request_is_served_from_the_cache(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(
            UserRepository,
            "get_user_by_id",
            wraps=UserRepository.get_user_by_id,
        ) as db_read:
            first = api_client.get(f"/users?user_id={user_id}", headers=headers)
            second = api_client.get(f"/users?user_id={user_id}", headers=headers)

        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert db_read.call_count == 1

    def test_an_empty_cache_still_serves_the_request(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        cache_key = f"user:{user_id}:{token}"

        first = api_client.get(f"/users?user_id={user_id}", headers=headers)
        cache_client.flushdb()
        assert get_cached(cache_key) is None

        second = api_client.get(f"/users?user_id={user_id}", headers=headers)

        assert second.status_code == 200
        assert second.json() == first.json()
        assert get_cached(cache_key) is not None

    def test_the_request_succeeds_when_redis_is_unreachable(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
        broken_redis,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]

        response = api_client.get(
            f"/users?user_id={user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["id"] == user_id

        assert broken_redis.get.called

    def test_a_corrupted_entry_is_discarded_and_the_request_still_succeeds(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        token = dummy_user_with_codeforces_handle["token"]
        user_id = dummy_user_with_codeforces_handle["user_id"]
        cache_key = f"user:{user_id}:{token}"

        cache_client.set(cache_key, "not-valid-json", ex=300)

        response = api_client.get(
            f"/users?user_id={user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestLeaderBoardCacheInRedis:

    @staticmethod
    def leaderboard_cache_key(limit: int) -> str:
        return (
            f"leaderboard:{limit}"
            f":{get_int('LEADERBOARD_MIN_CONTESTS')}"
            f":{get_int('LEADERBOARD_ACTIVE_WITHIN_DAYS')}"
        )

    def test_request_populates_redis_with_an_expiring_key(
            self,
            api_client
        ):
        limit = 5
        cache_key = self.leaderboard_cache_key(limit)

        assert get_cached(cache_key) is None

        response = api_client.get("/users/leaderboard", params={"limit": limit})
        assert response.status_code == 200

        assert get_cached(cache_key) is not None

        ttl = cache_client.ttl(cache_key)
        assert 0 < ttl <= LEADERBOARD_CACHE_TTL_SECONDS

    def test_the_cached_entry_rebuilds_the_response_model(
            self,
            api_client
        ):
        limit = 5
        cache_key = self.leaderboard_cache_key(limit)

        response = api_client.get("/users/leaderboard", params={"limit": limit})
        assert response.status_code == 200

        stored = get_cached(cache_key)
        assert stored is not None, "nothing was written to the cache"

        rebuilt = deserialize_models(stored, LeaderboardEntry)
        assert [entry.model_dump() for entry in rebuilt] == response.json()

    def test_a_second_request_is_served_from_the_cache(
            self,
            api_client
        ):
        params = {"limit": 5}

        with patch.object(
            UserRepository,
            "get_top_rated_users",
            wraps=UserRepository.get_top_rated_users,
        ) as db_read:
            first = api_client.get("/users/leaderboard", params=params)
            second = api_client.get("/users/leaderboard", params=params)

        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert db_read.call_count == 1

    def test_different_limits_do_not_share_an_entry(
            self,
            api_client
        ):
        api_client.get("/users/leaderboard", params={"limit": 5})
        api_client.get("/users/leaderboard", params={"limit": 20})

        assert get_cached(self.leaderboard_cache_key(5)) is not None
        assert get_cached(self.leaderboard_cache_key(20)) is not None

    def test_the_request_succeeds_when_redis_is_unreachable(
            self,
            api_client,
            broken_redis
        ):
        response = api_client.get("/users/leaderboard", params={"limit": 5})

        assert response.status_code == 200
        assert isinstance(response.json(), list)

        assert broken_redis.get.called

    def test_a_corrupted_entry_is_discarded_and_the_request_still_succeeds(
            self,
            api_client
        ):
        limit = 5
        cache_key = self.leaderboard_cache_key(limit)

        cache_client.set(cache_key, "not-valid-json", ex=300)

        response = api_client.get("/users/leaderboard", params={"limit": limit})
        assert response.status_code == 200

        stored = get_cached(cache_key)
        assert stored != "not-valid-json", "the corrupt entry was not discarded"
        assert [entry.model_dump() for entry in deserialize_models(stored, LeaderboardEntry)] == response.json()
