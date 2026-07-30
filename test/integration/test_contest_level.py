"""
Integration tests for contest level endpoints.
"""


class TestGetAllContestLevels:
    """
    Tests for the GET /contest-level endpoint.
    """

    def test_get_all_contest_levels_empty(
        self,
        api_client
    ):
        """
        When no contest levels exist in DB, returns empty list.
        """
        response = api_client.get("/contest-level")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_contest_levels_returns_created_levels(
        self,
        api_client,
        create_dummy_contest_level_20_and_21
    ):
        """
        When contest levels exist, returns them with expected fields.
        """
        response = api_client.get("/contest-level")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        level_20 = data[0]
        assert "id" in level_20
        assert level_20["level"] == 20
        assert level_20["duration_in_min"] == 120
        assert level_20["performance"] == 1575
        assert level_20["p1_rating"] == 1000
        assert level_20["p2_rating"] == 1200
        assert level_20["p3_rating"] == 1400
        assert level_20["p4_rating"] == 1500

        level_21 = data[1]
        assert "id" in level_21
        assert level_21["level"] == 21
        assert level_21["duration_in_min"] == 120
        assert level_21["performance"] == 1600
        assert level_21["p1_rating"] == 1000
        assert level_21["p2_rating"] == 1200
        assert level_21["p3_rating"] == 1400
        assert level_21["p4_rating"] == 1600

    

    def test_get_all_contest_levels_ordered_by_level(
        self,
        api_client,
        db
    ):
        """
        Contest levels are returned ordered by level ascending.
        """
        from api.contest_level.contest_level_services import ContestLevelService
        from api.contest_level.contest_level_response_models import ContestLevelInput

        ContestLevelService.create_contest_level(
            db=db,
            create_contest_level=ContestLevelInput(
                level=21,
                duration_in_min=120,
                performance=1600,
                p1_rating=1000,
                p2_rating=1200,
                p3_rating=1400,
                p4_rating=1600
            )
        )
        ContestLevelService.create_contest_level(
            db=db,
            create_contest_level=ContestLevelInput(
                level=20,
                duration_in_min=60,
                performance=1400,
                p1_rating=800,
                p2_rating=1000,
                p3_rating=1200,
                p4_rating=1400
            )
        )

        response = api_client.get("/contest-level")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["level"] == 20
        assert data[1]["level"] == 21
