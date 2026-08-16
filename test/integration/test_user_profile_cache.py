from api.cache.redis_client import client as cache_client
from api.user.user_response_models import UserResponseModel


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
        assert UserResponseModel.model_validate_json(stored).model_dump() == response.json()

    def test_a_second_request_returns_the_same_body(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        """
        The second request is served from Redis and must be indistinguishable
        from the first.
        """
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
