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