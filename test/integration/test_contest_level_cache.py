from unittest.mock import patch

from api.cache.redis_client import client as cache_client
from api.contest_level.contest_level_repository import ContestLevelRepository
from api.contest_level.contest_level_response_models import ContestLevelOutput
from api.utils import Utils

CONTEST_LEVEL_CACHE_TTL_SECONDS = 1440

CONTEST_LEVEL_CACHE_KEY = "contest_level"


class TestContestLevelCacheInRedis:
    """
    Reference data, public and unparameterised — the longest-lived cache in the
    codebase and the only one keyed on a bare prefix.
    """

    def test_request_populates_redis_with_an_expiring_key(
        self,
        api_client,
        create_dummy_contest_level_20_and_21,
    ):
        assert cache_client.get(CONTEST_LEVEL_CACHE_KEY) is None

        response = api_client.get("/contest-level")
        assert response.status_code == 200

        assert cache_client.get(CONTEST_LEVEL_CACHE_KEY) is not None

        # -1 would mean the entry never expires and is served forever;
        # -2 would mean it is already gone.
        ttl = cache_client.ttl(CONTEST_LEVEL_CACHE_KEY)
        assert CONTEST_LEVEL_CACHE_TTL_SECONDS - 5 <= ttl <= CONTEST_LEVEL_CACHE_TTL_SECONDS

    def test_the_cached_entry_rebuilds_the_response_model(
        self,
        api_client,
        create_dummy_contest_level_20_and_21,
    ):
        """
        This endpoint returns a list, not a single model, so it is stored via
        Utils.serialize_models. What comes back out has to be a list of
        ContestLevelOutput matching the response body.
        """
        response = api_client.get("/contest-level")
        assert response.status_code == 200

        stored = cache_client.get(CONTEST_LEVEL_CACHE_KEY)
        assert stored is not None, "nothing was written to the cache"

        rebuilt = Utils.deserialize_models(stored, ContestLevelOutput)
        assert [level.model_dump() for level in rebuilt] == response.json()

    def test_a_second_request_is_served_from_the_cache(
        self,
        api_client,
        create_dummy_contest_level_20_and_21,
    ):
        """
        The second request must not reach the database. Comparing bodies proves
        nothing on its own — two identical queries produce identical bodies too.
        The proof is that the repository is queried once across two requests.
        """
        with patch.object(
            ContestLevelRepository,
            "get_all_contest_levels",
            wraps=ContestLevelRepository.get_all_contest_levels,
        ) as db_read:
            first = api_client.get("/contest-level")
            second = api_client.get("/contest-level")

        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert db_read.call_count == 1

    def test_the_request_succeeds_when_redis_is_unreachable(
        self,
        api_client,
        create_dummy_contest_level_20_and_21,
        broken_redis,
    ):
        """
        A cache is an optimization, never a dependency. With Redis refusing
        every command the endpoint still answers, just from the database.
        """
        response = api_client.get("/contest-level")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        # The cache was consulted and failed, rather than being skipped.
        assert broken_redis.get.called

    def test_a_corrupted_entry_is_discarded_and_the_request_still_succeeds(
        self,
        api_client,
        create_dummy_contest_level_20_and_21,
    ):
        """
        An unreadable entry — truncated, or written by an older version of the
        model — must be dropped rather than raised on. The service deletes it,
        falls through to the database, and writes a readable entry back.
        """
        cache_client.set(CONTEST_LEVEL_CACHE_KEY, "not-valid-json", ex=3000)

        response = api_client.get("/contest-level")
        assert response.status_code == 200

        stored = cache_client.get(CONTEST_LEVEL_CACHE_KEY)
        assert stored != "not-valid-json", "the corrupt entry was not discarded"
        assert [
            level.model_dump()
            for level in Utils.deserialize_models(stored, ContestLevelOutput)
        ] == response.json()
