from api.cache.redis_client import client as cache_client
from api.contest_session.contest_session_response_models import (
    HeatgraphData,
    ContestHistoryOutput
)

HEATGRAPH_CACHE_TTL_SECONDS = 150
CONTEST_HISTORY_CACHE_TTL_SECONDS = 150


class TestHeatgraphCacheInRedis:

    def test_request_populates_redis_with_an_expiring_key(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]
        year = 2023

        cache_key = f"contest_session:{user_id}:year{year}"

        assert cache_client.get(cache_key) is None

        response = api_client.get(
            "/contest-session/heatgraph-data",
            params={"user_id": user_id, "year": year},
        )
        assert response.status_code == 200

        assert cache_client.get(cache_key) is not None

        ttl = cache_client.ttl(cache_key)
        assert 0 < ttl <= HEATGRAPH_CACHE_TTL_SECONDS

    def test_the_cached_entry_rebuilds_the_response_model(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]
        year = 2023
        cache_key = f"contest_session:{user_id}:year{year}"
        params = {"user_id": user_id, "year": year}

        first = api_client.get("/contest-session/heatgraph-data", params=params)
        assert first.status_code == 200

        stored = cache_client.get(cache_key)
        assert stored is not None, "nothing was written to the cache"

        rebuilt = HeatgraphData.model_validate_json(stored)
        assert rebuilt.model_dump(mode="json") == first.json()

        second = api_client.get("/contest-session/heatgraph-data", params=params)
        assert second.status_code == 200
        assert HeatgraphData.model_validate(second.json()) == rebuilt

    def test_the_request_succeeds_when_redis_is_unreachable(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
        broken_redis,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]

        response = api_client.get(
            "/contest-session/heatgraph-data",
            params={"user_id": user_id, "year": 2023},
        )

        assert response.status_code == 200
        assert "items" in response.json()
        assert broken_redis.get.called

    def test_a_corrupted_entry_is_discarded_and_the_request_still_succeeds(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]
        year = 2023
        cache_key = f"contest_session:{user_id}:year{year}"

        cache_client.set(cache_key, "not-valid-json", ex=300)

        response = api_client.get(
            "/contest-session/heatgraph-data",
            params={"user_id": user_id, "year": year},
        )
        assert response.status_code == 200

        stored = cache_client.get(cache_key)
        assert stored != "not-valid-json", "the corrupt entry was not discarded"
        assert HeatgraphData.model_validate_json(stored).model_dump(mode="json") == response.json()


class TestContestHistoryCacheInRedis:

    def test_request_populates_redis_with_an_expiring_key(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]
        skip, limit = 0, 10

        cache_key = f"contest_session:{user_id}:skip-{skip}:limit-{limit}"

        assert cache_client.get(cache_key) is None

        response = api_client.get(
            "/contest-session/history",
            params={"user_id": user_id, "skip": skip, "limit": limit},
        )
        assert response.status_code == 200

        assert cache_client.get(cache_key) is not None

        ttl = cache_client.ttl(cache_key)
        assert 0 < ttl <= CONTEST_HISTORY_CACHE_TTL_SECONDS

    def test_the_cached_entry_rebuilds_the_response_model(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]
        skip, limit = 0, 10
        cache_key = f"contest_session:{user_id}:skip-{skip}:limit-{limit}"
        params = {"user_id": user_id, "skip": skip, "limit": limit}

        first = api_client.get("/contest-session/history", params=params)
        assert first.status_code == 200

        stored = cache_client.get(cache_key)
        assert stored is not None, "nothing was written to the cache"

        rebuilt = ContestHistoryOutput.model_validate_json(stored)
        assert rebuilt.model_dump(mode="json") == first.json()

        second = api_client.get("/contest-session/history", params=params)
        assert second.status_code == 200
        assert ContestHistoryOutput.model_validate(second.json()) == rebuilt

    def test_the_request_succeeds_when_redis_is_unreachable(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
        broken_redis,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]

        response = api_client.get(
            "/contest-session/history",
            params={"user_id": user_id, "skip": 0, "limit": 10},
        )

        assert response.status_code == 200
        assert "items" in response.json()

        assert broken_redis.get.called

    def test_a_corrupted_entry_is_discarded_and_the_request_still_succeeds(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        user_id = dummy_user_with_codeforces_handle["user_id"]
        skip, limit = 0, 10
        cache_key = f"contest_session:{user_id}:skip-{skip}:limit-{limit}"

        cache_client.set(cache_key, "not-valid-json", ex=300)

        response = api_client.get(
            "/contest-session/history",
            params={"user_id": user_id, "skip": skip, "limit": limit},
        )
        assert response.status_code == 200

        stored = cache_client.get(cache_key)
        assert stored != "not-valid-json", "the corrupt entry was not discarded"
        assert ContestHistoryOutput.model_validate_json(stored).model_dump(mode="json") == response.json()
