from api.contest_theme.contest_theme_services import ContestThemeService
from api.contest_theme.contest_theme_response_models import ContestThemeOutput


class TestCreateContestTheme:
    """
    This test class runs test for create contest theme
    """

    def test_create_contest_theme_successful(self, api_client, db, admin_headers):
        """
        To test if a contest theme can be created successfully
        """
        request_body = {
            "theme": "test_theme"
        }
        create_response = api_client.post(
            "/contest-theme",
            json=request_body,
            headers=admin_headers,
        )

        assert create_response.status_code == 204

        contest_themes: list[ContestThemeOutput] = ContestThemeService.get_all_contest_themes(db=db)

        assert len(contest_themes) == 1
        print(contest_themes[0].theme)
        assert contest_themes[0].theme != "test_theme"
        assert contest_themes[0].theme == "TEST_THEME"


    def test_create_contest_theme_duplicate_theme(self, api_client, admin_headers):
        """
        To test that creating a contest theme with an existing theme returns 409.
        """
        request_body = {"theme": "duplicate_test_theme"}
        first_response = api_client.post(
            "/contest-theme",
            json=request_body,
            headers=admin_headers,
        )
        assert first_response.status_code == 204

        second_response = api_client.post(
            "/contest-theme",
            json=request_body,
            headers=admin_headers,
        )
        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": "Contest theme already exists"
        }

        # After the duplicate POST fails, the first theme must still be in the DB
        get_response = api_client.get("/contest-theme")
        assert get_response.status_code == 200
        assert len(get_response.json()) == 1
        assert get_response.json()[0]["theme"] == "DUPLICATE_TEST_THEME"


    def test_create_contest_theme_requires_admin_token(self, api_client, db):
        """
        To test that creating a contest theme without the admin token is rejected
        and does not write to the database.
        """
        response = api_client.post(
            "/contest-theme",
            json={"theme": "unauthorized_theme"},
        )
        assert response.status_code == 401

        assert ContestThemeService.get_all_contest_themes(db=db) == []


    def test_create_contest_theme_rejects_wrong_admin_token(self, api_client):
        """
        To test that a bearer token which is not the admin token is rejected.
        """
        response = api_client.post(
            "/contest-theme",
            json={"theme": "unauthorized_theme"},
            headers={"Authorization": "Bearer not-the-admin-token"},
        )
        assert response.status_code == 401


class TestGetAllContestThemes:
    """
    This test class runs test for get all contest themes
    """

    def test_get_all_contest_themes_successful(self, api_client, admin_headers):
        """
        To test if all contest themes can be fetched successfully
        """
        create_response = api_client.post(
            "/contest-theme",
            json={"theme": "test_theme"},
            headers=admin_headers,
        )
        assert create_response.status_code == 204

        response = api_client.get("/contest-theme")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["theme"] == "TEST_THEME"


    def test_get_all_contest_themes_empty(self, api_client):
        """
        To test if no contest themes are fetched when there are no contest themes in the database
        """

        response = api_client.get("/contest-theme")
        assert response.status_code == 200
        assert len(response.json()) == 0
        assert response.json() == []


    def test_get_multiple_contest_themes(self, api_client, admin_headers):
        """
        To test if multiple contest themes can be fetched successfully
        """
        create_response = api_client.post(
            "/contest-theme",
            json={"theme": "test_theme"},
            headers=admin_headers,
        )
        assert create_response.status_code == 204

        create_response = api_client.post(
            "/contest-theme",
            json={"theme": "test_theme_2"},
            headers=admin_headers,
        )
        assert create_response.status_code == 204

        response = api_client.get("/contest-theme")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["theme"] == "TEST_THEME"
        assert response.json()[1]["theme"] == "TEST_THEME_2"


    def test_get_all_contest_themes_is_public(self, api_client):
        """
        To test that reading contest themes does not require the admin token.
        """
        response = api_client.get("/contest-theme")
        assert response.status_code == 200
