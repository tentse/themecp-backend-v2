"""
Example integration test demonstrating database operations and Codeforces API mocking.

This test shows how to:
1. Use the test database session fixture
2. Mock Codeforces API calls
3. Test user registration and Codeforces handle verification flow
"""

from api.error_constants import ErrorConstants


class TestGetUser:
    """
    This test class runs get user details endpoints
    """

    def test_get_user_details_successful(
        self,
        api_client,
        dummy_user_without_codeforces_handle
    ):
        """
        To test if a registered user can get their details correctly.
        User without contests gets Unrated and null contest stats.
        """
        user_response = api_client.get(
            "/users",
            headers={
                "Authorization": f"Bearer {dummy_user_without_codeforces_handle["token"]}"
            }
        )

        assert user_response.status_code == 200
        user_data = user_response.json()
        assert user_data["email"] == dummy_user_without_codeforces_handle["email"]
        assert user_data["codeforces_handle"] is None
        assert user_data["rating"] is None
        assert user_data["max_contest_rating"] is None
        assert user_data["best_performance"] is None
        assert user_data["contest_attempts"] == 0
        assert user_data["rating_label"] == "Unrated"

    
    def test_get_user_invalid_token(self, api_client):
        """
        To test if a user is not registered and tries to get their details.
        """

        token = "Invalid token"

        user_response = api_client.get(
            "/users",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        assert user_response.status_code == 401
        user_data = user_response.json()
        assert user_data["detail"] == ErrorConstants.INVALID_TOKEN


    def test_get_user_with_codeforces_handle(
        self,
        api_client,
        dummy_user_with_codeforces_handle
    ):
        """
        To test if get codeforces handle when getting user detail.
        User without contests gets Unrated and null contest stats.
        """
        token = dummy_user_with_codeforces_handle['token']
        email = dummy_user_with_codeforces_handle['email']
        codeforces_handle = dummy_user_with_codeforces_handle['codeforces_handle']
        user_response = api_client.get(
            "/users",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        assert user_response.status_code == 200
        user_data = user_response.json()
        assert user_data["email"] == email
        assert user_data["codeforces_handle"] == codeforces_handle
        assert user_data["rating"] is None
        assert user_data["max_contest_rating"] is None
        assert user_data["best_performance"] is None
        assert user_data["contest_attempts"] == 0
        assert user_data["rating_label"] == "Unrated"



class TestViewUserProfile:
    """
    Tests for viewing a profile by user id on GET /users.

    The rule: email is returned only when the caller owns the profile. Everyone
    else — logged in as somebody else, or not logged in at all — gets the same
    profile with the email withheld.
    """

    def test_own_profile_by_id_includes_email(
        self,
        api_client,
        dummy_user_with_codeforces_handle
    ):
        """
        Asking for your own id while holding your own token is still you looking
        at yourself, so the email stays.
        """
        response = api_client.get(
            "/users",
            params={"user_id": dummy_user_with_codeforces_handle["user_id"]},
            headers={"Authorization": f"Bearer {dummy_user_with_codeforces_handle['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == dummy_user_with_codeforces_handle["email"]
        assert data["id"] == dummy_user_with_codeforces_handle["user_id"]

    def test_other_users_profile_hides_email_when_logged_in(
        self,
        api_client,
        db,
        dummy_user_with_codeforces_handle
    ):
        """
        A signed-in user viewing somebody else's profile must not see their email.
        """
        other = seed_rated_user(db, "someone_else", 1500, email="someone_else@example.com")

        response = api_client.get(
            "/users",
            params={"user_id": other.id},
            headers={"Authorization": f"Bearer {dummy_user_with_codeforces_handle['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] is None
        assert data["id"] == other.id
        assert "someone_else@example.com" not in response.text

    def test_other_users_profile_hides_email_when_anonymous(self, api_client, db):
        """
        No token at all: the profile is still viewable, the email still is not.
        """
        other = seed_rated_user(db, "public_profile", 1600, email="public_profile@example.com")

        response = api_client.get("/users", params={"user_id": other.id})

        assert response.status_code == 200
        data = response.json()
        assert data["email"] is None
        assert "public_profile@example.com" not in response.text

    def test_public_profile_returns_every_non_email_field(self, api_client, db):
        """
        Withholding the email must not blank out the rest of the profile — the
        whole point is that other people can see the stats.
        """
        other = seed_rated_user(
            db,
            "full_stats",
            1500,
            email="full_stats@example.com",
            max_contest_rating=1720,
            best_performance=1800,
        )

        response = api_client.get("/users", params={"user_id": other.id})

        assert response.status_code == 200
        data = response.json()
        assert data["email"] is None
        assert data["id"] == other.id
        assert data["codeforces_handle"] == "full_stats"
        assert data["rating"] == 1500
        assert data["max_contest_rating"] == 1720
        assert data["best_performance"] == 1800
        assert data["contest_attempts"] == 1
        assert data["rating_label"] == "Specialist"

    def test_profile_is_viewable_for_a_user_with_no_codeforces_handle(self, api_client, db):
        """
        Most accounts have no handle. Keying on id rather than handle is what
        makes their profiles reachable at all.
        """
        other = seed_rated_user(db, None, 1300, email="no_handle@example.com")

        response = api_client.get("/users", params={"user_id": other.id})

        assert response.status_code == 200
        data = response.json()
        assert data["codeforces_handle"] is None
        assert data["rating"] == 1300
        assert data["email"] is None

    def test_unknown_user_id_returns_404(self, api_client):
        """
        An id nobody owns is a missing profile, not an empty one.
        """
        response = api_client.get("/users", params={"user_id": "no_such_user_id"})

        assert response.status_code == 404
        assert response.json()["detail"] == ErrorConstants.USER_NOT_FOUND

    def test_no_user_id_and_no_token_is_unauthorized(self, api_client):
        """
        Without an id there is nothing to look up, so the caller must say who
        they are.
        """
        response = api_client.get("/users")

        assert response.status_code == 401
        assert response.json()["detail"] == ErrorConstants.UNAUTHORIZED

    def test_invalid_token_still_shows_the_public_profile(self, api_client, db):
        """
        A stale or malformed token only means "not the owner" when an id is
        given. Returning 401 here would sign a browsing user out of the app
        merely for looking at somebody else's profile.
        """
        other = seed_rated_user(db, "browsed_profile", 1400, email="browsed_profile@example.com")

        response = api_client.get(
            "/users",
            params={"user_id": other.id},
            headers={"Authorization": "Bearer this-is-not-a-valid-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] is None
        assert data["id"] == other.id

    def test_invalid_token_without_user_id_still_401s(self, api_client):
        """
        The other half of the rule: with nothing to look up, a bad token is a
        hard failure and keeps its original message.
        """
        response = api_client.get(
            "/users",
            headers={"Authorization": "Bearer this-is-not-a-valid-token"}
        )

        assert response.status_code == 401
        assert response.json()["detail"] == ErrorConstants.INVALID_TOKEN

    def test_no_user_id_with_token_is_unchanged(
        self,
        api_client,
        dummy_user_with_codeforces_handle
    ):
        """
        Backward compatibility: the frontend calls GET /users with no query
        parameter to load the signed-in user, and that must keep working.
        """
        response = api_client.get(
            "/users",
            headers={"Authorization": f"Bearer {dummy_user_with_codeforces_handle['token']}"}
        )

        assert response.status_code == 200
        assert response.json()["email"] == dummy_user_with_codeforces_handle["email"]


class TestGetCodeforcesProblemForHandleVerification:
    """
    This test class run test for getting codeforces problem
    """

    def test_get_handle_verification_cf_problem_endpoint(
        self,
        api_client,
        mock_codeforces_api,
        dummy_user_without_codeforces_handle
    ):
        """
        Test the /users/handle-verification-cf-problem endpoint using the mocked
        Codeforces API responses from the test fixtures.
        """
        # Arrange: register a user and obtain a JWT token
        token = dummy_user_without_codeforces_handle['token']

        codeforces_handle = "test_handle"

        # Act: call the endpoint through the shared TestClient
        response = api_client.get(
            "/users/handle-verification-cf-problem",
            params={"codeforces_handle": codeforces_handle},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert: HTTP response is OK and payload matches mocked Codeforces problem
        assert response.status_code == 200
        data = response.json()

        # Using the mocked default_problems_response from conftest.py:
        # first problem is contestId=5000, index="A", rating=1000, tags=["greedy", "dp"]
        assert data["contestID"] == "5000"
        assert data["index"] == "A"
        assert data["rating"] == 1000
        assert "greedy" in data["tags"]

        # Ensure the Codeforces API mock was actually used (no real HTTP calls)
        assert mock_codeforces_api.call_count > 0


class TestUpdateCodeforcesHandle:
    """
    This test class checks the update codeforces handle endpoint
    """

    def test_update_codeforces_handle_successfully(
        self,
        api_client,
        mock_codeforces_api,
        dummy_user_without_codeforces_handle
    ):
        """
        To test if a user can update their Codeforces handle successfully.
        """

        token = dummy_user_without_codeforces_handle['token']
        
        codeforces_handle_verification = {
            "codeforces_handle": "test_handle",
            "contestID": "1236",
            "index": "B"
        }

        response = api_client.put(
            "/users/codeforces-handle",
            json=codeforces_handle_verification,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert True == data

    
    def test_update_duplicated_codeforces_handle(
        self,
        api_client,
        mock_codeforces_api,
        dummy_user_without_codeforces_handle,
        dummy_user_with_codeforces_handle
    ):
        """
        To test if server is correctly restricting registration of duplicated codeforces handle
        """
        existing_codeforces_handle = dummy_user_with_codeforces_handle['codeforces_handle']

        token = dummy_user_without_codeforces_handle['token']

        codeforces_handle_verification = {
            "codeforces_handle": existing_codeforces_handle,
            "contestID": "1236",
            "index": "B"
        }

        response = api_client.put(
            "/users/codeforces-handle",
            json=codeforces_handle_verification,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data['detail'] == ErrorConstants.CODEFORCES_HANDLE_ALREADY_EXISTS

    
    def test_update_codeforces_handle_already_codeforces_handle_present(
        self,
        api_client,
        mock_codeforces_api,
        dummy_user_with_codeforces_handle
    ):
        """
        To test if server is able to reject if user tries to add codeforces handle
        and already handle is added for this user
        """
        token = dummy_user_with_codeforces_handle['token']

        codeforces_handle_verification = {
            "codeforces_handle": "new_codeforces_handle",
            "contestID": "1236",
            "index": "B"
        }

        response = api_client.put(
            "/users/codeforces-handle",
            json=codeforces_handle_verification,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data['detail'] == ErrorConstants.CODEFORCES_HANDLE_ALREADY_ADDED


    def test_update_codeforces_handle_unsuccessfully(
        self,
        api_client,
        mock_codeforces_api,
        dummy_user_without_codeforces_handle
    ):
        """
        To test if a user cannot update their Codeforces handle if they have not submitted a problem with the correct contestID and index.
        """

        token = dummy_user_without_codeforces_handle['token']
        
        codeforces_handle_verification = {
            "codeforces_handle": "test_handle",
            "contestID": "111111",
            "index": "Z"
        }

        response = api_client.put(
            "/users/codeforces-handle",
            json=codeforces_handle_verification,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert False == data


def seed_rated_user(
    db,
    codeforces_handle,
    contest_rating,
    email=None,
    max_contest_rating=None,
    best_performance=None,
    contest_attempts=None,
    last_active_days_ago=0,
):
    """
    Insert a user row directly, plus one finished contest to date their activity.

    Reading endpoints only need rows in `users`, so driving registration and a
    full contest just to set a rating would add noise without adding coverage.
    `contest_attempts` is NOT NULL, so it always gets a value.

    Leaderboard tests must pass `contest_attempts` explicitly, because the board
    filters on it. Left unset it stays at 1, which is what the profile tests
    expect and which is *below* the leaderboard minimum on purpose.

    The single session exists only to give the user a "last active" date for the
    leaderboard's recency filter. It deliberately does NOT match
    `contest_attempts` — the two filters read different sources, and seeding
    fifteen identical sessions per user would add no coverage.
    """
    from api.user.user_model import Users
    from api.utils import Utils

    if contest_attempts is None:
        contest_attempts = 1 if contest_rating is not None else 0

    user = Users(
        id=Utils.generate_id(),
        email=email or f"{Utils.generate_id()}@example.com",
        codeforces_handle=codeforces_handle,
        contest_rating=contest_rating,
        max_contest_rating=max_contest_rating,
        best_performance=best_performance,
        contest_attempts=contest_attempts,
    )
    db.add(user)

    if contest_rating is not None:
        db.add(seed_finished_session(user.id, days_ago=last_active_days_ago))

    db.flush()
    return user


def seed_finished_session(user_id, days_ago=0):
    """A finished contest session for `user_id`, dated `days_ago` days back."""
    import time

    from api.contest_session.contest_session_models import ContestSession
    from api.contest_session.contest_session_response_models import (
        ContestStatus,
        ProblemStatus,
    )
    from api.utils import Utils

    starts_at = int(time.time()) - days_ago * 86_400
    values = {
        "id": Utils.generate_id(),
        "user_id": user_id,
        "level": 21,
        "theme": "greedy",
        "duration_in_min": 120,
        "status": ContestStatus.FINISHED.value,
        "starts_at": starts_at,
        "ends_at": starts_at + 7_200,
        "performance": 1500,
        "rating_before": 1400,
        "rating_after": 1407,
        "rating_delta": 7,
    }
    for problem_number in (1, 2, 3, 4):
        values[f"p{problem_number}_cf_contestId"] = "999"
        values[f"p{problem_number}_cf_index"] = "ABCD"[problem_number - 1]
        values[f"p{problem_number}_rating"] = 1000 + problem_number * 100
        values[f"p{problem_number}_status"] = ProblemStatus.UNSOLVED.value
    return ContestSession(**values)


# Every leaderboard test seeds users at this many contests so they clear the
# minimum. Kept above it rather than exactly on it, so the boundary is tested in
# one place instead of accidentally everywhere.
QUALIFYING_CONTESTS = 15


class TestLeaderboard:
    """
    Tests for the public GET /users/leaderboard endpoint.
    """

    def test_leaderboard_empty(self, api_client):
        """
        With no users at all, the leaderboard is an empty list rather than an error.
        """
        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        assert response.json() == []

    def test_leaderboard_is_ordered_by_rating_descending(self, api_client, db):
        """
        Highest rating first.
        """
        seed_rated_user(db, "middle_handle", 1500, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "highest_handle", 2200, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "lowest_handle", 900, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert [row["codeforces_handle"] for row in data] == [
            "highest_handle",
            "middle_handle",
            "lowest_handle",
        ]
        assert [row["rating"] for row in data] == [2200, 1500, 900]

    def test_leaderboard_defaults_to_the_configured_limit(self, api_client, db):
        """
        Without an explicit limit the board holds `LEADERBOARD_DEFAULT_LIMIT`
        entries, and they are the highest rated — not the first ones found.

        Derived from the constant rather than hardcoded, because the limit is
        configurable per deployment and a fixed number here would fail the moment
        someone changed it.
        """
        from api.user.user_views import LEADERBOARD_DEFAULT_LIMIT

        seeded = LEADERBOARD_DEFAULT_LIMIT + 2
        for index in range(seeded):
            seed_rated_user(db, f"handle_{index:02d}", 1000 + index, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == LEADERBOARD_DEFAULT_LIMIT
        # highest seeded rating first, and the two lowest excluded
        assert data[0]["rating"] == 1000 + seeded - 1
        assert data[-1]["rating"] == 1000 + seeded - LEADERBOARD_DEFAULT_LIMIT

    def test_leaderboard_limit_is_configurable(self, api_client, db):
        """
        The whole point of the query parameter: 10 today, 15 tomorrow, no redeploy.
        """
        for index in range(20):
            seed_rated_user(db, f"handle_{index:02d}", 1000 + index, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard", params={"limit": 15})

        assert response.status_code == 200
        assert len(response.json()) == 15

    def test_leaderboard_excludes_users_without_a_codeforces_handle(self, api_client, db):
        """
        A row with no handle has nothing to display, so it is left out even when
        it outranks everyone. This is the agreed product rule and most of the
        highest-rated accounts in production are in exactly this state.
        """
        seed_rated_user(db, None, 3000, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "has_a_handle", 1200, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["codeforces_handle"] == "has_a_handle"
        assert all(row["rating"] != 3000 for row in data)

    def test_leaderboard_excludes_users_without_a_rating(self, api_client, db):
        """
        A user who has linked a handle but never finished a contest is unrated
        and has no place on a ranking.
        """
        seed_rated_user(db, "never_competed", None)
        seed_rated_user(db, "has_competed", 1100, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["codeforces_handle"] == "has_competed"

    def test_leaderboard_exposes_only_public_fields(self, api_client, db):
        """
        The endpoint is public, so the payload must carry nothing beyond what it
        needs to display — no email, no id. This guards against someone later
        reusing UserResponseModel, which carries both.
        """
        seed_rated_user(db, "privacy_check", 1700, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert set(data[0].keys()) == {"user_id", "codeforces_handle", "rating", "rating_label"}
        assert "email" not in response.text
        assert "@example.com" not in response.text

    def test_leaderboard_includes_rating_label(self, api_client, db):
        """
        The label comes from the backend so the frontend colours rows from one
        source of truth instead of its own copy of the thresholds.

        Ratings are checked on band boundaries, where an off-by-one would hide.
        """
        seed_rated_user(db, "newbie_edge", 1199, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "pupil_edge", 1200, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "grandmaster_edge", 2400, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "legendary_edge", 3000, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        labels = {
            row["codeforces_handle"]: row["rating_label"]
            for row in response.json()
        }
        assert labels == {
            "legendary_edge": "Legendary Grandmaster",
            "grandmaster_edge": "Grandmaster",
            "pupil_edge": "Pupil",
            "newbie_edge": "Newbie",
        }

    def test_leaderboard_label_matches_the_shared_rating_utility(self, api_client, db):
        """
        The endpoint must not grow its own thresholds — it has to agree with
        get_rating_label(), which /users already uses.
        """
        from api.user.rating_utils import get_rating_label

        seed_rated_user(db, "agreement_check", 2050, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        row = response.json()[0]
        assert row["rating_label"] == get_rating_label(row["rating"])

    def test_leaderboard_breaks_ties_deterministically(self, api_client, db):
        """
        Equal ratings must not reorder between identical calls. `codeforces_handle`
        is unique, so (rating DESC, handle ASC) is a total order.
        """
        seed_rated_user(db, "bravo_tied", 1800, contest_attempts=QUALIFYING_CONTESTS)
        seed_rated_user(db, "alpha_tied", 1800, contest_attempts=QUALIFYING_CONTESTS)

        first = api_client.get("/users/leaderboard").json()
        second = api_client.get("/users/leaderboard").json()

        assert [row["codeforces_handle"] for row in first] == ["alpha_tied", "bravo_tied"]
        assert first == second

    def test_leaderboard_rejects_out_of_range_limits(self, api_client):
        """
        Bounds are enforced by FastAPI, so a caller cannot ask for zero rows or
        pull the whole user table.
        """
        assert api_client.get("/users/leaderboard", params={"limit": 0}).status_code == 422
        assert api_client.get("/users/leaderboard", params={"limit": 101}).status_code == 422

    def test_leaderboard_needs_no_authentication(self, api_client, db):
        """
        Public, like /contest-level and /contest-theme — no Authorization header.
        """
        seed_rated_user(db, "public_view", 1300, contest_attempts=QUALIFYING_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        assert response.json()[0]["codeforces_handle"] == "public_view"
    def test_leaderboard_excludes_users_below_the_minimum_contest_count(
        self,
        api_client,
        db
    ):
        """
        A user's first contest seeds their rating from their live Codeforces
        rating, so a strong Codeforces competitor lands near the top of the board
        after one session. Requiring a minimum number of contests is what keeps
        the ranking about ThemeCP rather than about Codeforces.
        """
        from api.user.user_views import LEADERBOARD_MIN_CONTESTS

        seed_rated_user(
            db, "codeforces_tourist", 3000,
            contest_attempts=LEADERBOARD_MIN_CONTESTS - 1
        )
        seed_rated_user(
            db, "themecp_regular", 1200,
            contest_attempts=LEADERBOARD_MIN_CONTESTS
        )

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        handles = [row["codeforces_handle"] for row in data]
        assert handles == ["themecp_regular"], (
            "the 3000-rated user has too few contests and must not appear, "
            "even though they outrank everyone"
        )

    def test_leaderboard_includes_users_exactly_at_the_minimum(self, api_client, db):
        """
        The boundary itself qualifies — this is where an off-by-one would hide.
        """
        from api.user.user_views import LEADERBOARD_MIN_CONTESTS

        seed_rated_user(
            db, "exactly_at_minimum", 1500,
            contest_attempts=LEADERBOARD_MIN_CONTESTS
        )
        seed_rated_user(
            db, "one_short", 1600,
            contest_attempts=LEADERBOARD_MIN_CONTESTS - 1
        )

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        handles = [row["codeforces_handle"] for row in response.json()]
        assert handles == ["exactly_at_minimum"]

    def test_leaderboard_ordering_is_unaffected_by_the_minimum(self, api_client, db):
        """
        Among users who qualify, ranking is still purely by rating — activity is
        a gate, not a ranking factor.
        """
        from api.user.user_views import LEADERBOARD_MIN_CONTESTS

        seed_rated_user(db, "many_contests_low_rating", 1100,
                        contest_attempts=LEADERBOARD_MIN_CONTESTS * 5)
        seed_rated_user(db, "few_contests_high_rating", 2100,
                        contest_attempts=LEADERBOARD_MIN_CONTESTS)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        handles = [row["codeforces_handle"] for row in response.json()]
        assert handles == ["few_contests_high_rating", "many_contests_low_rating"]

    def test_leaderboard_excludes_users_inactive_beyond_the_window(
        self,
        api_client,
        db
    ):
        """
        The board is meant to show people still using ThemeCP. A high rating
        earned long ago should not hold a slot indefinitely.
        """
        from api.user.user_views import LEADERBOARD_ACTIVE_WITHIN_DAYS

        seed_rated_user(
            db, "long_retired", 3000,
            contest_attempts=QUALIFYING_CONTESTS,
            last_active_days_ago=LEADERBOARD_ACTIVE_WITHIN_DAYS + 30
        )
        seed_rated_user(
            db, "still_playing", 1200,
            contest_attempts=QUALIFYING_CONTESTS,
            last_active_days_ago=7
        )

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        handles = [row["codeforces_handle"] for row in response.json()]
        assert handles == ["still_playing"], (
            "a 3000-rated user who stopped playing must not outrank an active one"
        )

    def test_leaderboard_includes_users_exactly_at_the_activity_boundary(
        self,
        api_client,
        db
    ):
        """
        The cutoff is inclusive — the boundary day still counts as active.
        """
        from api.user.user_views import LEADERBOARD_ACTIVE_WITHIN_DAYS

        seed_rated_user(
            db, "on_the_boundary", 1500,
            contest_attempts=QUALIFYING_CONTESTS,
            last_active_days_ago=LEADERBOARD_ACTIVE_WITHIN_DAYS - 1
        )
        seed_rated_user(
            db, "one_day_too_old", 1600,
            contest_attempts=QUALIFYING_CONTESTS,
            last_active_days_ago=LEADERBOARD_ACTIVE_WITHIN_DAYS + 1
        )

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        handles = [row["codeforces_handle"] for row in response.json()]
        assert handles == ["on_the_boundary"]

    def test_leaderboard_applies_both_filters_independently(self, api_client, db):
        """
        Activity and contest count are separate gates. Passing one must not
        excuse failing the other — easy to get wrong if either is implemented as
        a replacement rather than an addition.
        """
        from api.user.user_views import (
            LEADERBOARD_ACTIVE_WITHIN_DAYS,
            LEADERBOARD_MIN_CONTESTS,
        )

        # enough contests, but stopped playing
        seed_rated_user(
            db, "experienced_but_gone", 2500,
            contest_attempts=LEADERBOARD_MIN_CONTESTS,
            last_active_days_ago=LEADERBOARD_ACTIVE_WITHIN_DAYS + 1
        )
        # playing today, but too few contests
        seed_rated_user(
            db, "active_but_new", 2400,
            contest_attempts=LEADERBOARD_MIN_CONTESTS - 1,
            last_active_days_ago=0
        )
        # clears both
        seed_rated_user(
            db, "qualifies", 1300,
            contest_attempts=LEADERBOARD_MIN_CONTESTS,
            last_active_days_ago=0
        )

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        handles = [row["codeforces_handle"] for row in response.json()]
        assert handles == ["qualifies"]

    def test_leaderboard_ignores_activity_from_unfinished_contests(self, api_client, db):
        """
        Starting a contest and never finishing it is not activity — otherwise a
        user could hold a leaderboard slot without completing anything.
        """
        from api.contest_session.contest_session_response_models import ContestStatus
        from api.user.user_views import LEADERBOARD_ACTIVE_WITHIN_DAYS

        user = seed_rated_user(
            db, "abandoned_contests", 2000,
            contest_attempts=QUALIFYING_CONTESTS,
            last_active_days_ago=LEADERBOARD_ACTIVE_WITHIN_DAYS + 30
        )
        running = seed_finished_session(user.id, days_ago=0)
        running.status = ContestStatus.RUNNING.value
        db.add(running)
        db.flush()

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        assert response.json() == []
