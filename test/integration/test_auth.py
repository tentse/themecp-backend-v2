from api.auth.auth_services import AuthService
from api.error_constants import ErrorConstants

class TestAuthRegistration:
    """
    This test class run test for auth registration
    """

    def test_auth_registration_successful(self, api_client):
        """
        Example integration test using the shared api_client fixture.

        It demonstrates how to call real endpoints through the client:
        - POST /auth/register
        - POST /auth/login
        """
        auth_credentials = {
            "email": "test_user@example.com"
        }

        # Register the user
        register_resp = api_client.post(
            "/auth/register",
            json=auth_credentials
        )

        assert register_resp.status_code == 201

        register_data = register_resp.json()

        assert "token" in register_data


    def test_auth_registration_duplicate_email(
        self,
        api_client,
        dummy_user_without_codeforces_handle
    ):
        """
        To test if server throws error if duplicate email is restricted
        """

        email = dummy_user_without_codeforces_handle['email']

        auth_credentials = {
            "email": email
        }

        register_resp = api_client.post(
            "/auth/register",
            json=auth_credentials
        )

        assert register_resp.status_code == 409
        data = register_resp.json()
        assert data['detail'] == ErrorConstants.USER_ALREADY_EXISTS

    
    def test_auth_registration_invalid_request_body(self, api_client):
        """
        To test if a user provides an invalid request body.
        """

        auth_credentials = "Invalid request body"

        register_data = api_client.post(
            "/auth/register",
            json=auth_credentials
        )

        assert register_data.status_code == 422
    

class TestAuthLogin:
    """
    This test class runs auth login
    """
    
    def test_auth_login_successful(self, api_client, db):
        """
        Test that a user can login if they have been registered successfully.
        """

        test_email = "test_user@example.com"

        AuthService.auth_register_service(
            db=db,
            email=test_email
        )

        auth_credentials = {
            "email": test_email
        }

        login_data = api_client.post(
            "/auth/login",
            json=auth_credentials
        )

        assert login_data.status_code == 200

        login_data = login_data.json()

        assert "token" in login_data


    def test_auth_unauthorized_login(self, api_client):
        """
        To test if a user is not registered and tries to login.
        """

        test_email = "test_user@example.com"

        auth_credentials = {
            "email": test_email
        }

        login_data = api_client.post(
            "/auth/login",
            json=auth_credentials
        )

        assert login_data.status_code == 401
        data = login_data.json()

        assert data["detail"] == ErrorConstants.UNAUTHORIZED
