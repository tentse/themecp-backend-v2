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


def seed_rated_user(db, codeforces_handle, contest_rating):
    """
    Insert a user row directly.

    The leaderboard only reads `users`, so driving registration and a full
    contest just to set a rating would add noise without adding coverage.
    `contest_attempts` is NOT NULL, so it always gets a value.
    """
    from api.user.user_model import Users
    from api.utils import Utils

    user = Users(
        id=Utils.generate_id(),
        email=f"{Utils.generate_id()}@example.com",
        codeforces_handle=codeforces_handle,
        contest_rating=contest_rating,
        contest_attempts=1 if contest_rating is not None else 0,
    )
    db.add(user)
    db.flush()
    return user


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
        seed_rated_user(db, "middle_handle", 1500)
        seed_rated_user(db, "highest_handle", 2200)
        seed_rated_user(db, "lowest_handle", 900)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert [row["codeforces_handle"] for row in data] == [
            "highest_handle",
            "middle_handle",
            "lowest_handle",
        ]
        assert [row["rating"] for row in data] == [2200, 1500, 900]

    def test_leaderboard_defaults_to_top_ten(self, api_client, db):
        """
        Without an explicit limit the board holds ten entries, and they are the
        ten highest — not the first ten found.
        """
        for index in range(12):
            seed_rated_user(db, f"handle_{index:02d}", 1000 + index)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert data[0]["rating"] == 1011
        assert data[-1]["rating"] == 1002

    def test_leaderboard_limit_is_configurable(self, api_client, db):
        """
        The whole point of the query parameter: 10 today, 15 tomorrow, no redeploy.
        """
        for index in range(20):
            seed_rated_user(db, f"handle_{index:02d}", 1000 + index)

        response = api_client.get("/users/leaderboard", params={"limit": 15})

        assert response.status_code == 200
        assert len(response.json()) == 15

    def test_leaderboard_excludes_users_without_a_codeforces_handle(self, api_client, db):
        """
        A row with no handle has nothing to display, so it is left out even when
        it outranks everyone. This is the agreed product rule and most of the
        highest-rated accounts in production are in exactly this state.
        """
        seed_rated_user(db, None, 3000)
        seed_rated_user(db, "has_a_handle", 1200)

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
        seed_rated_user(db, "has_competed", 1100)

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
        seed_rated_user(db, "privacy_check", 1700)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert set(data[0].keys()) == {"codeforces_handle", "rating", "rating_label"}
        assert "email" not in response.text
        assert "@example.com" not in response.text

    def test_leaderboard_includes_rating_label(self, api_client, db):
        """
        The label comes from the backend so the frontend colours rows from one
        source of truth instead of its own copy of the thresholds.

        Ratings are checked on band boundaries, where an off-by-one would hide.
        """
        seed_rated_user(db, "newbie_edge", 1199)
        seed_rated_user(db, "pupil_edge", 1200)
        seed_rated_user(db, "grandmaster_edge", 2400)
        seed_rated_user(db, "legendary_edge", 3000)

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

        seed_rated_user(db, "agreement_check", 2050)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        row = response.json()[0]
        assert row["rating_label"] == get_rating_label(row["rating"])

    def test_leaderboard_breaks_ties_deterministically(self, api_client, db):
        """
        Equal ratings must not reorder between identical calls. `codeforces_handle`
        is unique, so (rating DESC, handle ASC) is a total order.
        """
        seed_rated_user(db, "bravo_tied", 1800)
        seed_rated_user(db, "alpha_tied", 1800)

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
        seed_rated_user(db, "public_view", 1300)

        response = api_client.get("/users/leaderboard")

        assert response.status_code == 200
        assert response.json()[0]["codeforces_handle"] == "public_view"