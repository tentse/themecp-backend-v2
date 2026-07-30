from api.contest_session.contest_session_services import ContestSessionService
from api.contest_session.contest_session_response_models import ContestStatus, ProblemStatus
import time
from unittest.mock import Mock, patch
from api.error_constants import ErrorConstants


class TestCreateContestSession:
    """
    This test class contains test related to creation of contest session
    """

    def test_create_contest_session_successful(
        self,
        api_client,
        mock_codeforces_api,
        dummy_user_with_codeforces_handle,
        create_dummy_contest_level_20_and_21
    ):
        """
        This test case checks for successful contest session creation
        """
        request_body = {
            "level": 21,
            "theme": "greedy"
        }

        token = dummy_user_with_codeforces_handle['token']

        response = api_client.post(
            "/contest-session",
            json=request_body,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data['status'] == ContestStatus.REVIEW.value
        assert data['user_id'] == dummy_user_with_codeforces_handle['user_id']
        assert data['starts_at'] is None
        assert data['ends_at'] is None

        assert data['p1'] is not None
        assert data['p1']['rating'] is not None
        assert data['p1']['rating'] == 1000

        assert data['p2'] is not None
        assert data['p2']['rating'] is not None
        assert data['p2']['rating'] == 1200

        assert data['p3'] is not None
        assert data['p3']['rating'] is not None
        assert data['p3']['rating'] == 1400

        assert data['p4'] is not None
        assert data['p4']['rating'] is not None
        assert data['p4']['rating'] == 1600

    
    def test_create_contest_session_when_session_is_review_returns_same_session(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """
        This test checks whether server is restricting user from creating duplicate
        contest when already a contest is in REVIEW
        """
        token = create_dummy_in_review_contest_session_level_21_theme_greedy['token']

        request_body = {
            "level": 20,
            "theme": "greedy"
        }

        response = api_client.post(
            "/contest-session",
            json=request_body,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data['status'] == ContestStatus.REVIEW.value
        assert data['p1'] is not None
        assert data['p1']['rating'] is not None
        assert data['p1']['rating'] == 1000
        assert data['p2'] is not None
        assert data['p2']['rating'] is not None
        assert data['p2']['rating'] == 1200
        assert data['p3'] is not None
        assert data['p3']['rating'] is not None
        assert data['p3']['rating'] == 1400
        assert data['p4'] is not None
        assert data['p4']['rating'] is not None
        assert data['p4']['rating'] == 1600


    def test_create_contest_session_when_session_is_running_returns_same_session(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy
    ):
        """
        This test checks whether server restricts creating a new contest
        when a contest is already RUNNING
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']

        request_body = {
            "level": 20,
            "theme": "greedy",
        }

        response = api_client.post(
            "/contest-session",
            json=request_body,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data['status'] == ContestStatus.RUNNING.value
        assert data['p1'] is not None
        assert data['p1']['rating'] is not None
        assert data['p1']['rating'] == 1000
        assert data['p2'] is not None
        assert data['p2']['rating'] is not None
        assert data['p2']['rating'] == 1200
        assert data['p3'] is not None
        assert data['p3']['rating'] is not None
        assert data['p3']['rating'] == 1400
        assert data['p4'] is not None
        assert data['p4']['rating'] is not None
        assert data['p4']['rating'] == 1600

    
    def test_create_contest_session_user_without_codeforces_handle(
        self,
        api_client,
        dummy_user_without_codeforces_handle
    ):
        """
        This test checks whether server restricts creating a new contest
        when user does not have a codeforces handle
        """
        token = dummy_user_without_codeforces_handle['token']
        request_body = {
            "level": 21,
            "theme": "greedy"
        }
        response = api_client.post(
            "/contest-session",
            json=request_body,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data['detail'] == ErrorConstants.CODEFORCES_HANDLE_NOT_ADDED


class TestGetContestSession:
    """
    This test class test /GET contest session endpoint
    """

    def test_contest_session_in_review_state(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        token = create_dummy_in_review_contest_session_level_21_theme_greedy['token']

        response = api_client.get(
            "/contest-session",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data['status'] == ContestStatus.REVIEW.value

    
    def test_get_contest_session_returns_running_session(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        This test checks whether server returns running session when session is RUNNING
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        response = api_client.get(
            "/contest-session",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == ContestStatus.RUNNING.value
        assert data['duration_in_min'] == 120
        assert data['starts_at'] is not None
        assert data['ends_at'] is not None

    def test_get_contest_session_returns_new_session_after_finish_and_create(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
        db
    ):
        """
        After ending a contest and creating a new one, GET /contest-session should
        return the new REVIEW session, not the old FINISHED one.
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        old_session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        # Patch user.status for empty submissions so end can proceed
        TestEndContestSession()._patch_user_status(mock_codeforces_api, [])

        # End the running contest
        ContestSessionService.end_contest_session(
            db=db,
            token=token,
            contest_session_id=old_session_id
        )

        # Create a new contest session
        create_response = api_client.post(
            "/contest-session",
            json={
                "level": 20,
                "theme": "dp"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 201
        new_session = create_response.json()
        assert new_session['id'] != old_session_id
        assert new_session['status'] == ContestStatus.REVIEW.value
        assert new_session['level'] == 20
        assert new_session['theme'] == "dp"
        assert new_session['duration_in_min'] == 120
        assert new_session['p1']['rating'] == 1000
        assert new_session['p2']['rating'] == 1200
        assert new_session['p3']['rating'] == 1400
        assert new_session['p4']['rating'] == 1500



class TestStartContestSession:
    """
    This test class tests the POST /contest-session/start endpoint
    """

    def test_start_contest_session_successful(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """
        Test that a contest session can be started successfully
        """
        token = create_dummy_in_review_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy['contest_session']['id']

        # Record time before starting
        time_before = int(time.time())

        response = api_client.put(
            f"/contest-session/{session_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data['id'] == session_id
        assert data['status'] == ContestStatus.RUNNING.value
        assert 'starts_at' in data
        assert 'ends_at' in data
        assert 'duration_in_min' in data
        assert 'p1' in data
        assert 'p2' in data
        assert 'p3' in data
        assert 'p4' in data

        # Verify starts_at is approximately 15 seconds from now
        # Allow some tolerance for test execution time
        expected_start = time_before + 15
        expected_ends = expected_start + 120 * 60
        assert data['starts_at'] >= expected_start
        assert data['starts_at'] <= expected_start + 5  # 5 second tolerance
        assert data['ends_at'] is not None
        assert data['ends_at'] == expected_ends


    def test_start_contest_session_updates_status_to_running(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """
        Test that starting a contest changes its status to RUNNING
        """
        token = create_dummy_in_review_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy['contest_session']['id']

        # Start the contest
        response = api_client.put(
            f"/contest-session/{session_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == session_id
        assert data['status'] == ContestStatus.RUNNING.value
        assert data['starts_at'] is not None
        assert data['ends_at'] is not None

    def test_start_contest_session_fails_with_invalid_session_id(
        self,
        api_client,
        dummy_user_with_codeforces_handle
    ):
        """
        Test that starting a contest fails when there's no session in REVIEW status
        """
        token = dummy_user_with_codeforces_handle['token']
        session_id = "invalid-session-id"

        response = api_client.put(
            f"/contest-session/{session_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_NOT_FOUND


    def test_start_contest_session_fails_when_session_already_running(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy
    ):
        """
        Test that starting a contest fails when the session is already RUNNING
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        response = api_client.put(
            f"/contest-session/{session_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_ALREADY_RUNNING

    def test_start_contest_session_creates_problem_status_records(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy,
        db
    ):
        """
        Test that starting a contest creates problem status records for all 4 problems
        """
        from api.contest_session.contest_session_models import ContestSessionProblemsStatus

        token = create_dummy_in_review_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy['contest_session']['id']

        # Start the contest
        api_client.put(
            f"/contest-session/{session_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Query the database directly to verify problem status records were created
        problem_statuses = db.query(ContestSessionProblemsStatus).filter(
            ContestSessionProblemsStatus.session_id == session_id
        ).all()

        # Verify 4 problem status records were created
        assert len(problem_statuses) == 4

        # Verify each record has correct initial state
        for status in problem_statuses:
            assert status.status == ProblemStatus.UNSOLVED.value
            assert status.accepted_at is None
            assert status.solved_in_min is None

        # Verify problem numbers are 1, 2, 3, 4
        problem_numbers = sorted([s.problem_number for s in problem_statuses])
        assert problem_numbers == [1, 2, 3, 4]


class TestDeleteContestSessionInReviewStatus:
    """
    Tests for DELETE /contest-session/{contest_session_id} (delete session in REVIEW only).
    """

    def test_delete_contest_session_in_review_success(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """
        Delete own contest session in REVIEW returns 204 and session is removed.
        """
        token = create_dummy_in_review_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy['contest_session']['id']

        response = api_client.delete(
            f"/contest-session/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

        # Verify session is gone: GET /contest-session returns 404 when no active session
        get_response = api_client.get(
            "/contest-session",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404
        assert get_response.json()['detail'] == ErrorConstants.CONTEST_SESSION_NOT_FOUND

    def test_delete_contest_session_not_found_returns_404(
        self,
        api_client,
        dummy_user_with_codeforces_handle
    ):
        """
        Delete with non-existent session id returns 404.
        """
        token = dummy_user_with_codeforces_handle['token']
        session_id = "invalid-session-id"

        response = api_client.delete(
            f"/contest-session/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_NOT_FOUND

    def test_delete_contest_session_when_running_returns_409(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy
    ):
        """
        Delete when session is RUNNING returns 409 (only REVIEW can be deleted).
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        response = api_client.delete(
            f"/contest-session/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_NOT_REVIEW

    def _make_mock_user_status_response(self, submissions):
        """Helper for mock user.status response."""
        result = []
        for s in submissions:
            result.append({
                "problem": {
                    "contestId": s["contestId"],
                    "index": s["index"],
                    "rating": s.get("rating", 0),
                    "tags": s.get("tags", [])
                },
                "verdict": s["verdict"],
                "creationTimeSeconds": s["creationTimeSeconds"]
            })
        return {"status": "OK", "result": result}

    def _patch_user_status(self, mock_codeforces_api, submissions):
        """Override mock_codeforces_api to return custom user.status."""
        custom_user_status = self._make_mock_user_status_response(submissions)
        original_side_effect = mock_codeforces_api.side_effect

        def custom_mock_get(url, **kwargs):
            mock_response = Mock()
            if "/user.status" in url:
                mock_response.json.return_value = custom_user_status
            else:
                return original_side_effect(url, **kwargs)
            return mock_response

        mock_codeforces_api.side_effect = custom_mock_get

    def test_delete_contest_session_when_finished_returns_409(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Delete when session is FINISHED returns 409 (only REVIEW can be deleted).
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        self._patch_user_status(mock_codeforces_api, [])

        api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        response = api_client.delete(
            f"/contest-session/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_NOT_REVIEW

    def test_delete_contest_session_without_auth_returns_403(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """
        Delete without Authorization header returns 403.
        """
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy['contest_session']['id']

        response = api_client.delete(
            f"/contest-session/{session_id}"
        )

        assert response.status_code == 403


class TestRefreshProblemStatus:
    """
    This test class tests the POST /contest-session/refresh endpoint
    """

    def _make_mock_user_status_response(self, submissions):
        """
        Helper to create a mock user.status response with given submissions.
        Each submission is a dict with contestId, index, rating, verdict, creationTimeSeconds.
        """
        result = []
        for submission in submissions:
            result.append({
                "problem": {
                    "contestId": submission["contestId"],
                    "index": submission["index"],
                    "rating": submission.get("rating", 0),
                    "tags": submission.get("tags", [])
                },
                "verdict": submission["verdict"],
                "creationTimeSeconds": submission["creationTimeSeconds"]
            })
        return {
            "status": "OK",
            "result": result
        }

    def _patch_user_status(self, mock_codeforces_api, submissions):
        """
        Override the mock_codeforces_api to return a custom user.status response
        while keeping the problemset.problems mock intact.
        """
        custom_user_status = self._make_mock_user_status_response(submissions)

        original_side_effect = mock_codeforces_api.side_effect

        def custom_mock_get(url, **kwargs):
            mock_response = Mock()
            if "/user.status" in url:
                mock_response.json.return_value = custom_user_status
            else:
                return original_side_effect(url, **kwargs)
            return mock_response

        mock_codeforces_api.side_effect = custom_mock_get

    def test_refresh_first_problem_solved(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test that refreshing marks the first problem as SOLVED when
        user has an accepted submission for it after contest start time.
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        # Problem 1 is contestId=5000, index=A (based on mock data with greedy tag, rating 1000)
        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']

        submission_time = starts_at + 300  # Solved 5 minutes after start

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": submission_time,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data['contest_session_id'] == session_id
        assert data['starts_at'] == starts_at
        assert data['ends_at'] == starts_at + 120 * 60
        assert data['p1_status'] == ProblemStatus.SOLVED.value
        assert data['p2_status'] == ProblemStatus.UNSOLVED.value
        assert data['p3_status'] == ProblemStatus.UNSOLVED.value
        assert data['p4_status'] == ProblemStatus.UNSOLVED.value

    def test_refresh_sequential_order_enforced(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test that problem 2 stays UNSOLVED even if user solved it,
        when problem 1 has not been solved yet.
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p2_contest_id = int(contest_session['p2']['contestId'])
        p2_index = contest_session['p2']['index']

        submission_time = starts_at + 600

        # Only problem 2 is solved, problem 1 is NOT solved
        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p2_contest_id,
                "index": p2_index,
                "rating": 1200,
                "verdict": "OK",
                "creationTimeSeconds": submission_time,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['contest_session_id'] == session_id
        assert data['starts_at'] == starts_at
        assert data['ends_at'] == starts_at + 120 * 60
        assert data['p1_status'] == ProblemStatus.UNSOLVED.value
        assert data['p2_status'] == ProblemStatus.UNSOLVED.value
        assert data['p3_status'] == ProblemStatus.UNSOLVED.value
        assert data['p4_status'] == ProblemStatus.UNSOLVED.value


    def test_refresh_multiple_problems_solved_in_order(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test that problems 1 and 2 are both marked SOLVED when both
        have accepted submissions.
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']
        p2_contest_id = int(contest_session['p2']['contestId'])
        p2_index = contest_session['p2']['index']

        p1_submission_time = starts_at + 300   # 5 minutes
        p2_submission_time = starts_at + 900   # 15 minutes

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": p1_submission_time,
                "tags": ["greedy"]
            },
            {
                "contestId": p2_contest_id,
                "index": p2_index,
                "rating": 1200,
                "verdict": "OK",
                "creationTimeSeconds": p2_submission_time,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['contest_session_id'] == session_id
        assert data['starts_at'] == starts_at
        assert data['ends_at'] == starts_at + 120 * 60
        assert data['p1_status'] == ProblemStatus.SOLVED.value
        assert data['p2_status'] == ProblemStatus.SOLVED.value
        assert data['p3_status'] == ProblemStatus.UNSOLVED.value
        assert data['p4_status'] == ProblemStatus.UNSOLVED.value

    def test_refresh_problem_b_solved_before_a_does_not_count(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        When B is solved earlier (by time) than A on Codeforces, B must not count as solved.
        Only A is marked SOLVED; B, C, D stay UNSOLVED.
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']
        p2_contest_id = int(contest_session['p2']['contestId'])
        p2_index = contest_session['p2']['index']

        p1_submission_time = starts_at + 15 * 60   # 15 minutes
        p2_submission_time = starts_at + 5 * 60   # 5 minutes (before A)

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": p1_submission_time,
                "tags": ["greedy"]
            },
            {
                "contestId": p2_contest_id,
                "index": p2_index,
                "rating": 1200,
                "verdict": "OK",
                "creationTimeSeconds": p2_submission_time,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['contest_session_id'] == session_id
        assert data['starts_at'] == starts_at
        assert data['ends_at'] == starts_at + 120 * 60
        assert data['p1_status'] == ProblemStatus.SOLVED.value
        assert data['p2_status'] == ProblemStatus.UNSOLVED.value
        assert data['p3_status'] == ProblemStatus.UNSOLVED.value
        assert data['p4_status'] == ProblemStatus.UNSOLVED.value

    def test_refresh_no_session_returns_404(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
        mock_codeforces_api
    ):
        """
        Test that refreshing fails with 404 when there's no RUNNING session.
        """
        token = dummy_user_with_codeforces_handle['token']
        session_id = "invalid-session-id"

        response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_NOT_FOUND

    def test_refresh_already_solved_problems_not_overwritten(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
        db
    ):
        """
        Test that refreshing again does not overwrite already solved problems.
        Problem 1 is solved on first refresh; second refresh should keep the
        same accepted_at and solved_in_min values.
        """
        from api.contest_session.contest_session_models import ContestSessionProblemsStatus

        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']

        submission_time = starts_at + 300

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": submission_time,
                "tags": ["greedy"]
            }
        ])

        # First refresh
        first_response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert first_response.status_code == 200
        first_data = first_response.json()
        assert first_data['contest_session_id'] == session_id
        assert first_data['starts_at'] == starts_at
        assert first_data['ends_at'] == starts_at + 120 * 60
        assert first_data['p1_status'] == ProblemStatus.SOLVED.value

        # Fetch solved-at timing from DB after first refresh
        p1_after_first = db.query(ContestSessionProblemsStatus).filter(
            ContestSessionProblemsStatus.session_id == session_id,
            ContestSessionProblemsStatus.problem_number == 1
        ).one()
        first_accepted_at = p1_after_first.accepted_at
        first_solved_in_min = p1_after_first.solved_in_min

        # Second refresh with same data
        second_response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert second_data['p1_status'] == ProblemStatus.SOLVED.value

        # Fetch solved-at timing from DB after second refresh
        p1_after_second = db.query(ContestSessionProblemsStatus).filter(
            ContestSessionProblemsStatus.session_id == session_id,
            ContestSessionProblemsStatus.problem_number == 1
        ).one()
        second_accepted_at = p1_after_second.accepted_at
        second_solved_in_min = p1_after_second.solved_in_min

        # Timing must not be overwritten
        assert first_accepted_at == second_accepted_at
        assert first_solved_in_min == second_solved_in_min
        assert first_accepted_at == str(submission_time)
        assert first_solved_in_min == 5  # 300 seconds = 5 minutes


    def test_refresh_ignores_submissions_before_contest_start(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test that submissions made before the contest started are ignored.
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']

        # Submission happened BEFORE contest started
        submission_time = starts_at - 100

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": submission_time,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['contest_session_id'] == session_id
        assert data['starts_at'] == starts_at
        assert data['ends_at'] == starts_at + 120 * 60
        assert data['p1_status'] == ProblemStatus.UNSOLVED.value


class TestEndContestSession:
    """
    This test class tests the POST /contest-session/end endpoint
    """

    def _make_mock_user_status_response(self, submissions):
        """
        Helper to create a mock user.status response with given submissions.
        """
        result = []
        for s in submissions:
            result.append({
                "problem": {
                    "contestId": s["contestId"],
                    "index": s["index"],
                    "rating": s.get("rating", 0),
                    "tags": s.get("tags", [])
                },
                "verdict": s["verdict"],
                "creationTimeSeconds": s["creationTimeSeconds"]
            })
        return {"status": "OK", "result": result}

    def _patch_user_status(self, mock_codeforces_api, submissions):
        """
        Override the mock_codeforces_api to return a custom user.status response
        while keeping the problemset.problems mock intact.
        """
        custom_user_status = self._make_mock_user_status_response(submissions)
        original_side_effect = mock_codeforces_api.side_effect

        def custom_mock_get(url, **kwargs):
            mock_response = Mock()
            if "/user.status" in url:
                mock_response.json.return_value = custom_user_status
            else:
                return original_side_effect(url, **kwargs)
            return mock_response

        mock_codeforces_api.side_effect = custom_mock_get

    def test_end_contest_no_problems_solved(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test ending a contest with no problems solved.
        Performance = p1_rating - 50 = 1000 - 50 = 950
        Rating = round(950/15 + 1400*14/15) = round(1370.0) = 1370
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        # No submissions - empty list
        self._patch_user_status(mock_codeforces_api, [])

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

    def test_end_contest_first_problem_solved(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test ending a contest with only problem 1 solved in 5 minutes.
        time_limit = 135 (level=21)
        Performance = round((5/135)*1000 + ((135-5)/135)*1200) = round(1192.593) = 1193
        Rating = round(1193/15 + 1400*14/15) = round(1386.2) = 1386
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']

        submission_time = starts_at + 300  # 5 minutes

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": submission_time,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

    def test_end_contest_all_four_problems_solved(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api
    ):
        """
        Test ending a contest with all 4 problems solved.
        time_limit_all_solved = 120 (level=21), t4 = 60 minutes
        Performance = round((60/120)*1600 + ((120-60)/120)*(1600+400) + ((21-1)%4)*12.5)
                    = round(800 + 1000 + 0) = 1800
        Rating = round(1800/15 + 1400*14/15) = round(1426.667) = 1427
        """
        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']

        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']
        p2_contest_id = int(contest_session['p2']['contestId'])
        p2_index = contest_session['p2']['index']
        p3_contest_id = int(contest_session['p3']['contestId'])
        p3_index = contest_session['p3']['index']
        p4_contest_id = int(contest_session['p4']['contestId'])
        p4_index = contest_session['p4']['index']

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 600,
                "tags": ["greedy"]
            },
            {
                "contestId": p2_contest_id,
                "index": p2_index,
                "rating": 1200,
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 1200,
                "tags": ["greedy"]
            },
            {
                "contestId": p3_contest_id,
                "index": p3_index,
                "rating": 1400,
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 1800,
                "tags": ["greedy"]
            },
            {
                "contestId": p4_contest_id,
                "index": p4_index,
                "rating": 1600,
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 3600,
                "tags": ["greedy"]
            }
        ])

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

    def test_end_contest_no_running_session_returns_404(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
        mock_codeforces_api
    ):
        """
        Test that ending a contest fails with 404 when there's no RUNNING session.
        """
        token = dummy_user_with_codeforces_handle['token']
        session_id = "invalid-session-id"

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data['detail'] == ErrorConstants.CONTEST_SESSION_NOT_FOUND

    def test_end_contest_saves_result_to_db(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
        db
    ):
        """
        Test that ending a contest creates a ContestSessionResult record in the DB.
        """
        from api.contest_session.contest_session_models import ContestSessionResult

        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        # No submissions
        self._patch_user_status(mock_codeforces_api, [])

        api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Query DB directly
        result = db.query(ContestSessionResult).filter(
            ContestSessionResult.session_id == session_id
        ).first()

        assert result is not None
        assert result.solved_count == 0
        assert result.performance == 950
        assert result.rating_before == 1400
        assert result.rating_after == 1370
        assert result.rating_delta == -30

    def test_end_contest_first_contest_uses_codeforces_rating_when_present(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
        db
    ):
        """
        When user has no TheMCP rating but has a Codeforces rating, use CF rating as rating_before.
        """
        from api.contest_session.contest_session_models import ContestSessionResult
        from unittest.mock import Mock

        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']
        starts_at = contest_session['starts_at']
        session_id = contest_session['id']
        p1_contest_id = int(contest_session['p1']['contestId'])
        p1_index = contest_session['p1']['index']

        user_info_with_rating = {"status": "OK", "result": [{"handle": "test", "rating": 1600}]}
        user_status_one_solved = self._make_mock_user_status_response([
            {
                "contestId": p1_contest_id,
                "index": p1_index,
                "rating": 1000,
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 300,
                "tags": ["greedy"]
            }
        ])
        original_side_effect = mock_codeforces_api.side_effect

        def mock_get_with_cf_rating_and_status(url, **kwargs):
            mock_response = Mock()
            if "/user.info" in url:
                mock_response.json.return_value = user_info_with_rating
                return mock_response
            if "/user.status" in url:
                mock_response.json.return_value = user_status_one_solved
                return mock_response
            return original_side_effect(url, **kwargs)

        mock_codeforces_api.side_effect = mock_get_with_cf_rating_and_status

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        result = db.query(ContestSessionResult).filter(
            ContestSessionResult.session_id == session_id
        ).first()

        assert result is not None
        assert result.rating_before == 1600
        # One problem solved in 5 min: perf ~1193, rating_after = round(1193/15 + 1600*14/15) = 1573
        assert result.rating_after == 1573
        assert result.rating_delta == 1573 - 1600

    def test_end_contest_first_contest_uses_1400_when_codeforces_rating_null(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
        db
    ):
        """
        When user has no TheMCP rating and Codeforces rating is null (unrated), use 1400 as rating_before.
        """
        from api.contest_session.contest_session_models import ContestSessionResult

        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        # Default mock already returns user.info with rating None
        self._patch_user_status(mock_codeforces_api, [])

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        result = db.query(ContestSessionResult).filter(
            ContestSessionResult.session_id == session_id
        ).first()

        assert result is not None
        assert result.rating_before == 1400
        assert result.rating_after == 1370
        assert result.rating_delta == -30

    def test_end_contest_with_previous_contest_result(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
        db
    ):
        """
        Test that when a user has a previous contest result, the rating_before
        uses the previous rating_after value instead of default 1400.
        """
        from api.contest_session.contest_session_models import (
            ContestSessionResult,
            ContestSession
        )

        token = create_dummy_running_contest_session_level_21_theme_greedy['token']
        session_id = create_dummy_running_contest_session_level_21_theme_greedy['contest_session']['id']

        # Manually insert a previous finished session with a result.
        # Create a fake previous finished session for the same user
        current_session = db.query(ContestSession).filter(
            ContestSession.id == session_id
        ).first()
        user_id = current_session.user_id

        previous_session = ContestSession(
            id="previous-session-id",
            user_id=user_id,
            level=21,
            theme="greedy",
            duration_in_min=120,
            status=ContestStatus.FINISHED.value,
            starts_at=1000000,
            p1_cf_contestId="999",
            p1_cf_index="A",
            p2_cf_contestId="999",
            p2_cf_index="B",
            p3_cf_contestId="999",
            p3_cf_index="C",
            p4_cf_contestId="999",
            p4_cf_index="D"
        )
        db.add(previous_session)

        previous_result = ContestSessionResult(
            session_id="previous-session-id",
            solved_count=2,
            performance=1500,
            rating_before=1400,
            rating_after=1407,
            rating_delta=7
        )
        db.add(previous_result)
        db.flush()

        # No submissions for the current contest
        self._patch_user_status(mock_codeforces_api, [])

        response = api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204


class TestGetContestHistory:
    """
    Tests for GET /contest-session/history endpoint.
    """

    def _patch_user_status(self, mock_codeforces_api, submissions):
        """Override user.status mock response."""
        result = []
        for s in submissions:
            result.append({
                "problem": {
                    "contestId": s["contestId"],
                    "index": s["index"],
                    "rating": s.get("rating", 0),
                    "tags": s.get("tags", [])
                },
                "verdict": s["verdict"],
                "creationTimeSeconds": s["creationTimeSeconds"]
            })
        custom_user_status = {"status": "OK", "result": result}
        original_side_effect = mock_codeforces_api.side_effect

        def custom_mock_get(url, **kwargs):
            mock_response = Mock()
            if "/user.status" in url:
                mock_response.json.return_value = custom_user_status
            else:
                return original_side_effect(url, **kwargs)
            return mock_response

        mock_codeforces_api.side_effect = custom_mock_get

    def test_empty_history_when_no_finished_contests(
        self,
        api_client,
        dummy_user_with_codeforces_handle,
    ):
        """User with no finished contests gets empty history."""
        token = dummy_user_with_codeforces_handle["token"]

        response = api_client.get(
            "/contest-session/history",
            params={"skip": 0, "limit": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["skip"] == 0
        assert data["limit"] == 10
        assert data["total"] == 0

    def test_history_returns_finished_contests_in_order(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
    ):
        """Finished contest appears in history, latest first."""
        token = create_dummy_running_contest_session_level_21_theme_greedy["token"]
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy["contest_session"]
        starts_at = contest_session["starts_at"]
        session_id = contest_session["id"]

        p1 = contest_session["p1"]
        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": int(p1["contestId"]),
                "index": p1["index"],
                "rating": p1["rating"],
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 300,
                "tags": ["greedy"]
            }
        ])

        api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        response = api_client.get(
            "/contest-session/history",
            params={"skip": 0, "limit": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["skip"] == 0
        assert data["limit"] == 10

        item = data["items"][0]
        assert "date" in item
        assert item["date"]  # YYYY-MM-DD format
        assert item["level"] == 21
        assert item["theme"] == "greedy"
        assert "rating" in item
        assert "p1" in item
        assert "p2" in item
        assert item["p1_solved_in_min"] == 5  # starts_at + 300s = 5 min
        assert item["p2_solved_in_min"] is None
        assert item["p3_solved_in_min"] is None
        assert item["p4_solved_in_min"] is None

    def test_history_includes_solved_in_min_for_multiple_problems(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
    ):
        """History item includes solved_in_min for each solved problem (5 min and 15 min)."""
        token = create_dummy_running_contest_session_level_21_theme_greedy["token"]
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy["contest_session"]
        starts_at = contest_session["starts_at"]
        session_id = contest_session["id"]
        p1 = contest_session["p1"]
        p2 = contest_session["p2"]

        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": int(p1["contestId"]),
                "index": p1["index"],
                "rating": p1["rating"],
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 300,
                "tags": ["greedy"]
            },
            {
                "contestId": int(p2["contestId"]),
                "index": p2["index"],
                "rating": p2["rating"],
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 900,
                "tags": ["greedy"]
            },
        ])

        api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        response = api_client.get(
            "/contest-session/history",
            params={"skip": 0, "limit": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["p1_solved_in_min"] == 5   # 300s
        assert item["p2_solved_in_min"] == 15  # 900s
        assert item["p3_solved_in_min"] is None
        assert item["p4_solved_in_min"] is None

    def test_history_excludes_review_and_running(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy,
    ):
        """History excludes sessions in REVIEW status."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]

        response = api_client.get(
            "/contest-session/history",
            params={"skip": 0, "limit": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_history_pagination_skip_limit(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy,
        mock_codeforces_api,
    ):
        """Pagination skip and limit work correctly."""
        token = create_dummy_running_contest_session_level_21_theme_greedy["token"]
        contest_session = create_dummy_running_contest_session_level_21_theme_greedy["contest_session"]
        starts_at = contest_session["starts_at"]
        session_id = contest_session["id"]

        p1 = contest_session["p1"]
        self._patch_user_status(mock_codeforces_api, [
            {
                "contestId": int(p1["contestId"]),
                "index": p1["index"],
                "rating": p1["rating"],
                "verdict": "OK",
                "creationTimeSeconds": starts_at + 300,
                "tags": ["greedy"]
            }
        ])

        api_client.put(
            f"/contest-session/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        response = api_client.get(
            "/contest-session/history",
            params={"skip": 1, "limit": 5},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["skip"] == 1
        assert data["limit"] == 5
        assert data["total"] == 1


class TestReRollContestSessionProblem:
    """
    Tests for PUT /contest-session/{contest_session_id}/re-roll-problem endpoint.
    """

    def test_re_roll_contest_session_problem_2_successful(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """User can re-roll a problem successfully; response has correct shape and status."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        initial_contest_session = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]
        session_id = initial_contest_session["id"]

        response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/2",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["status"] == ContestStatus.REVIEW.value
        assert "p1" in data and "p2" in data and "p3" in data and "p4" in data
        for key in ("p1", "p2", "p3", "p4"):
            assert "contestId" in data[key]
            assert "index" in data[key]
            assert "rating" in data[key]
        # Other slots unchanged
        assert data["p1"]["contestId"] == initial_contest_session["p1"]["contestId"]
        assert data["p1"]["index"] == initial_contest_session["p1"]["index"]
        assert data["p3"]["contestId"] == initial_contest_session["p3"]["contestId"]
        assert data["p3"]["index"] == initial_contest_session["p3"]["index"]
        assert data["p4"]["contestId"] == initial_contest_session["p4"]["contestId"]
        assert data["p4"]["index"] == initial_contest_session["p4"]["index"]

        assert not (data["p2"]["contestId"] == initial_contest_session["p2"]["contestId"] and data["p2"]["index"] == initial_contest_session["p2"]["index"])
        assert not(data["p2"]["contestId"] == initial_contest_session["p1"]["contestId"] and data["p2"]["index"] == initial_contest_session["p1"]["index"])
        assert not(data["p2"]["contestId"] == initial_contest_session["p3"]["contestId"] and data["p2"]["index"] == initial_contest_session["p3"]["index"])
        assert not(data["p2"]["contestId"] == initial_contest_session["p4"]["contestId"] and data["p2"]["index"] == initial_contest_session["p4"]["index"])

    def test_re_roll_contest_session_problem_3_successful(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """User can re-roll a problem successfully; response has correct shape and status."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        initial_contest_session = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]
        session_id = initial_contest_session["id"]

        response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/3",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["status"] == ContestStatus.REVIEW.value
        assert "p1" in data and "p2" in data and "p3" in data and "p4" in data
        for key in ("p1", "p2", "p3", "p4"):
            assert "contestId" in data[key]
            assert "index" in data[key]
            assert "rating" in data[key]
        # Other slots unchanged
        assert data["p1"]["contestId"] == initial_contest_session["p1"]["contestId"]
        assert data["p1"]["index"] == initial_contest_session["p1"]["index"]
        assert data["p2"]["contestId"] == initial_contest_session["p2"]["contestId"]
        assert data["p2"]["index"] == initial_contest_session["p2"]["index"]
        assert data["p4"]["contestId"] == initial_contest_session["p4"]["contestId"]
        assert data["p4"]["index"] == initial_contest_session["p4"]["index"]

        assert not (data["p3"]["contestId"] == initial_contest_session["p3"]["contestId"] and data["p3"]["index"] == initial_contest_session["p3"]["index"])
        assert not(data["p3"]["contestId"] == initial_contest_session["p1"]["contestId"] and data["p3"]["index"] == initial_contest_session["p1"]["index"])
        assert not (data["p3"]["contestId"] == initial_contest_session["p3"]["contestId"] and data["p3"]["index"] == initial_contest_session["p3"]["index"])
        assert not(data["p3"]["contestId"] == initial_contest_session["p1"]["contestId"] and data["p3"]["index"] == initial_contest_session["p1"]["index"])
        assert not(data["p3"]["contestId"] == initial_contest_session["p2"]["contestId"] and data["p3"]["index"] == initial_contest_session["p2"]["index"])
        assert not(data["p3"]["contestId"] == initial_contest_session["p4"]["contestId"] and data["p3"]["index"] == initial_contest_session["p4"]["index"])


    def test_re_roll_fails_invalid_contest_session_id(
        self,
        api_client,
        dummy_user_with_codeforces_handle
    ):
        """Re-roll with non-existent or wrong-owner session id returns 404."""
        token = dummy_user_with_codeforces_handle["token"]
        session_id = "non-existent-session-id"

        response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == ErrorConstants.CONTEST_SESSION_NOT_FOUND


    def test_re_roll_fails_invalid_problem_number_zero(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """Re-roll with problem_number=0 returns 400."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]["id"]

        response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == ErrorConstants.INVALID_PROBLEM_NUMBER

    def test_re_roll_fails_invalid_problem_number_five(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """Re-roll with problem_number=5 returns 400."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        session_id = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]["id"]

        response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/5",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == ErrorConstants.INVALID_PROBLEM_NUMBER


    def test_re_roll_fails_session_not_in_review(
        self,
        api_client,
        create_dummy_running_contest_session_level_21_theme_greedy
    ):
        """Re-roll when session is RUNNING returns 409."""
        token = create_dummy_running_contest_session_level_21_theme_greedy["token"]
        session_id = create_dummy_running_contest_session_level_21_theme_greedy["contest_session"]["id"]

        response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == ErrorConstants.CONTEST_SESSION_NOT_REVIEW

    def test_re_roll_persisted_in_contest_session_and_reflected_in_get(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """Re-rolled problem is saved in contest_session and reflected in GET contest session."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        initial_contest_session = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]
        session_id = initial_contest_session["id"]

        re_roll_response = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert re_roll_response.status_code == 200
        re_roll_data = re_roll_response.json()
        new_p2 = (re_roll_data["p2"]["contestId"], re_roll_data["p2"]["index"])

        get_response = api_client.get(
            "/contest-session",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == session_id
        assert get_data["status"] == ContestStatus.REVIEW.value
        assert get_data["p2"]["contestId"] == new_p2[0]
        assert get_data["p2"]["index"] == new_p2[1]
        assert get_data["p1"]["contestId"] == initial_contest_session["p1"]["contestId"]
        assert get_data["p1"]["index"] == initial_contest_session["p1"]["index"]
        assert get_data["p3"]["contestId"] == initial_contest_session["p3"]["contestId"]
        assert get_data["p4"]["contestId"] == initial_contest_session["p4"]["contestId"]

    def test_re_roll_saved_in_seen_problems(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """Re-rolled problem is in seen set; second re-roll of same slot yields another new problem."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        initial_contest_session = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]
        session_id = initial_contest_session["id"]
        initial_p2 = initial_contest_session["p2"]

        first = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert first.status_code == 200
        first_p2 = first.json()["p2"]
        first_key = (str(first_p2["contestId"]), first_p2["index"])
        assert first_key != (str(initial_p2["contestId"]), initial_p2["index"])

        second = api_client.put(
            f"/contest-session/{session_id}/re-roll-problem/2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert second.status_code == 200
        second_p2 = second.json()["p2"]
        second_key = (str(second_p2["contestId"]), second_p2["index"])
        assert second_key != first_key
        assert second_key != (str(initial_p2["contestId"]), initial_p2["index"])

        get_response = api_client.get(
            "/contest-session",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        assert get_response.json()["p2"]["contestId"] == second_p2["contestId"]
        assert get_response.json()["p2"]["index"] == second_p2["index"]

    def test_re_roll_keeps_old_problem_in_seen_so_first_problem_never_returns(
        self,
        api_client,
        create_dummy_in_review_contest_session_level_21_theme_greedy
    ):
        """After multiple re-rolls, the very first problem (from contest creation) never reappears."""
        token = create_dummy_in_review_contest_session_level_21_theme_greedy["token"]
        contest_session = create_dummy_in_review_contest_session_level_21_theme_greedy["contest_session"]
        session_id = contest_session["id"]
        initial_p2 = contest_session["p2"]
        first_ever_key = (str(initial_p2["contestId"]), initial_p2["index"])

        seen_p2_keys = [first_ever_key]
        for _ in range(2):
            response = api_client.put(
                f"/contest-session/{session_id}/re-roll-problem/2",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            p2 = response.json()["p2"]
            key = (str(p2["contestId"]), p2["index"])
            assert key not in seen_p2_keys, (
                "Re-rolled problem must not repeat any previously seen problem for this slot"
            )
            seen_p2_keys.append(key)

        # The very first problem (from contest creation) must never have been re-offered
        assert first_ever_key not in seen_p2_keys[1:], (
            "The original problem from contest creation must not reappear after re-rolls"
        )