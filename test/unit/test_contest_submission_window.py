"""Submission deadlines through refresh and contest finalization, without a DB."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from api.codeforces.codeforces_response_model import UserSubmittedProblem
from api.codeforces.codeforces_utils import CodeforcesUtils
from api.contest_level.contest_level_services import ContestLevelService
from api.contest_session.contest_session_models import ContestSession
from api.contest_session.contest_session_repository import ContestSessionRepository
from api.contest_session.contest_session_response_models import ContestStatus, ProblemStatus
from api.contest_session.contest_session_services import ContestSessionService
from api.user.user_repository import UserRepository
from api.user.user_services import UserService


@pytest.fixture
def running_contest(monkeypatch):
    """Use real session slots and mock only authentication, I/O, and persistence."""
    starts_at = 1_700_000_000
    session = ContestSession(
        id="session-1", user_id="user-1", level=21, theme="greedy",
        duration_in_min=120, status=ContestStatus.RUNNING,
        starts_at=starts_at, ends_at=starts_at + 120 * 60,
    )
    for number, rating in enumerate((1000, 1200, 1400, 1600), start=1):
        setattr(session, f"p{number}_cf_contestId", str(100 + number))
        setattr(session, f"p{number}_cf_index", "A")
        setattr(session, f"p{number}_rating", rating)
        setattr(session, f"p{number}_status", ProblemStatus.UNSOLVED)

    user = SimpleNamespace(
        id=session.user_id, codeforces_handle="test_cf",
        max_contest_rating=None, best_performance=None, contest_attempts=0,
    )
    monkeypatch.setattr(UserService, "get_user_detail_from_token", lambda **kwargs: user)
    monkeypatch.setattr(UserRepository, "get_user_by_id", lambda **kwargs: user)
    monkeypatch.setattr(UserRepository, "update_user_contest_stats", MagicMock())
    monkeypatch.setattr(
        ContestLevelService, "get_problem_level_ratings",
        lambda **kwargs: SimpleNamespace(p1_rating=1000, p2_rating=1200, p3_rating=1400, p4_rating=1600),
    )
    monkeypatch.setattr(
        ContestSessionRepository, "get_contest_session_by_id_and_user_id", lambda **kwargs: session,
    )
    monkeypatch.setattr(
        ContestSessionRepository, "get_problem_statuses_by_id", lambda **kwargs: session.problem_slots(),
    )
    monkeypatch.setattr(ContestSessionRepository, "get_last_contest_result", lambda **kwargs: None)

    def update_problem_status(*, problem_number, state, accepted_at, solved_in_min, **kwargs):
        setattr(session, f"p{problem_number}_status", state)
        setattr(session, f"p{problem_number}_accepted_at", accepted_at)
        setattr(session, f"p{problem_number}_solved_in_min", solved_in_min)

    def save_contest_result(*, performance, rating_before, rating_after, rating_delta, **kwargs):
        session.performance = performance
        session.rating_before = rating_before
        session.rating_after = rating_after
        session.rating_delta = rating_delta
        session.status = ContestStatus.FINISHED

    monkeypatch.setattr(ContestSessionRepository, "update_problem_status", update_problem_status)
    monkeypatch.setattr(ContestSessionRepository, "save_contest_result", save_contest_result)
    submissions = MagicMock(return_value=[])
    monkeypatch.setattr(CodeforcesUtils, "get_user_submitted_problems", submissions)
    monkeypatch.setattr(CodeforcesUtils, "get_user_rating", lambda *args: None)
    return SimpleNamespace(session=session, db=MagicMock(), submissions=submissions)


def accepted_submission(session, number, timestamp):
    return UserSubmittedProblem(
        contestID=getattr(session, f"p{number}_cf_contestId"),
        index=getattr(session, f"p{number}_cf_index"),
        rating=getattr(session, f"p{number}_rating"), tags=[],
        verdict="OK", creationTimeSeconds=timestamp,
    )


def refresh(contest):
    return ContestSessionService.refresh_problem_status_service(
        db=contest.db, token="test-token", contest_session_id=contest.session.id,
    )


def test_late_accepted_submission_stays_unsolved(running_contest):
    session = running_contest.session
    running_contest.submissions.return_value = [accepted_submission(session, 1, session.ends_at + 1)]

    result = refresh(running_contest)

    assert result.p1.status == ProblemStatus.UNSOLVED
    assert result.p1.solved_in_min is None
    assert session.p1_accepted_at is None


@pytest.mark.parametrize("timestamp_offset,expected", [
    (-1, ProblemStatus.UNSOLVED),
    (0, ProblemStatus.SOLVED),
    (7199, ProblemStatus.SOLVED),
    (7200, ProblemStatus.UNSOLVED),
])
def test_refresh_respects_start_and_end_boundaries(running_contest, timestamp_offset, expected):
    session = running_contest.session
    timestamp = session.starts_at + timestamp_offset
    running_contest.submissions.return_value = [accepted_submission(session, 1, timestamp)]

    result = refresh(running_contest)

    assert result.p1.status == expected
    if expected == ProblemStatus.SOLVED:
        assert session.p1_accepted_at == timestamp
        assert result.p1.solved_in_min == timestamp_offset // 60
    else:
        assert session.p1_accepted_at is None
        assert result.p1.solved_in_min is None


def test_late_resubmission_does_not_replace_an_in_time_solve(running_contest):
    session = running_contest.session
    in_time = session.starts_at + 300
    running_contest.submissions.return_value = [
        accepted_submission(session, 1, session.ends_at + 60),
        accepted_submission(session, 1, in_time),
    ]

    result = refresh(running_contest)

    assert result.p1.status == ProblemStatus.SOLVED
    assert session.p1_accepted_at == in_time
    assert result.p1.solved_in_min == 5


def test_refresh_after_deadline_still_counts_in_time_submission(running_contest, monkeypatch):
    session = running_contest.session
    monkeypatch.setattr("api.contest_session.contest_session_services.time.time", lambda: session.ends_at + 60)
    running_contest.submissions.return_value = [accepted_submission(session, 1, session.ends_at - 1)]

    result = refresh(running_contest)

    assert result.p1.status == ProblemStatus.SOLVED
    assert session.p1_accepted_at == session.ends_at - 1


def test_in_time_first_problem_does_not_allow_late_second_problem(running_contest):
    session = running_contest.session
    running_contest.submissions.return_value = [
        accepted_submission(session, 1, session.starts_at + 300),
        accepted_submission(session, 2, session.ends_at + 1),
    ]

    result = refresh(running_contest)

    assert result.p1.status == ProblemStatus.SOLVED
    assert result.p2.status == ProblemStatus.UNSOLVED
    assert result.p2.solved_in_min is None
    assert session.p2_accepted_at is None


def test_finalization_does_not_score_late_solve(running_contest):
    session = running_contest.session
    running_contest.submissions.return_value = [accepted_submission(session, 1, session.ends_at + 1)]

    ContestSessionService.end_contest_session(
        db=running_contest.db, token="test-token", contest_session_id=session.id,
    )

    assert session.status == ContestStatus.FINISHED
    assert all(slot.status == ProblemStatus.UNSOLVED for slot in session.problem_slots())
    assert session.p1_accepted_at is None
    assert session.p1_solved_in_min is None
    assert session.performance == 950
    assert session.rating_after == 1370
