"""
Unit tests for orchestrator.session_tracker.SessionTracker.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

import orchestrator.session_tracker as st_module
from orchestrator.session_tracker import SessionTracker


def make_interview(
    session_id="session_1",
    candidate_id="candidate_1",
    status="PROCESSING",
    risk_score=None,
    assigned_node=None,
    start_time=None,
    end_time=None,
    created_at=None,
    updated_at=None,
):
    session = MagicMock()
    session.session_id = session_id
    session.candidate_id = candidate_id
    session.status = status
    session.risk_score = risk_score
    session.assigned_node = assigned_node
    session.start_time = start_time
    session.end_time = end_time
    session.created_at = created_at
    session.updated_at = updated_at
    return session


def make_db_session(rows=None):
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows or []
    db.execute.return_value = result
    return db


@pytest.fixture
def tracker():
    return SessionTracker()


def test_get_completed_sessions_returns_completed_sessions(tracker):
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    end_time = datetime.now(timezone.utc)

    session = make_interview(
        session_id="completed_1",
        candidate_id="candidate_1",
        status="COMPLETED",
        risk_score=0.75,
        start_time=start_time,
        end_time=end_time,
    )

    db = make_db_session([session])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_completed_sessions(limit=10)

    assert len(result) == 1
    assert result[0]["session_id"] == "completed_1"
    assert result[0]["candidate_id"] == "candidate_1"
    assert result[0]["status"] == "COMPLETED"
    assert result[0]["risk_score"] == 0.75
    assert result[0]["start_time"] == start_time.isoformat()
    assert result[0]["end_time"] == end_time.isoformat()
    assert result[0]["duration_seconds"] == pytest.approx(600, abs=1)

    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_completed_sessions_returns_empty_list_when_no_sessions(tracker):
    db = make_db_session([])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_completed_sessions(limit=10)

    assert result == []
    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_stuck_sessions_returns_processing_sessions_past_timeout(tracker):
    start_time = datetime.now(timezone.utc) - timedelta(minutes=60)

    session = make_interview(
        session_id="stuck_1",
        candidate_id="candidate_1",
        status="PROCESSING",
        assigned_node="worker-1",
        start_time=start_time,
    )

    db = make_db_session([session])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_stuck_sessions(timeout_minutes=30)

    assert len(result) == 1
    assert result[0]["session_id"] == "stuck_1"
    assert result[0]["candidate_id"] == "candidate_1"
    assert result[0]["status"] == "PROCESSING"
    assert result[0]["assigned_node"] == "worker-1"
    assert result[0]["start_time"] == start_time.isoformat()
    assert result[0]["elapsed_seconds"] > 0

    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_worker_distribution_counts_active_sessions(tracker):
    sessions = [
        make_interview(
            session_id="s1",
            status="PROCESSING",
            assigned_node="worker-1",
        ),
        make_interview(
            session_id="s2",
            status="VIDEO_PROCESSING",
            assigned_node="worker-1",
        ),
        make_interview(
            session_id="s3",
            status="EVALUATING",
            assigned_node="worker-2",
        ),
        make_interview(
            session_id="s4",
            status="PROCESSING",
            assigned_node=None,
        ),
    ]

    db = make_db_session(sessions)

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_worker_distribution()

    assert result == {
        "worker-1": 2,
        "worker-2": 1,
        "unassigned": 1,
    }

    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_failed_sessions_returns_failed_terminal_sessions(tracker):
    start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    end_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    updated_time = datetime.now(timezone.utc)

    sessions = [
        make_interview(
            session_id="failed_1",
            candidate_id="candidate_1",
            status="FAILED",
            risk_score=0.4,
            assigned_node="worker-1",
            start_time=start_time,
            end_time=end_time,
            updated_at=updated_time,
        ),
        make_interview(
            session_id="timeout_1",
            candidate_id="candidate_2",
            status="TIMEOUT",
            risk_score=0.2,
            assigned_node=None,
            start_time=start_time,
            end_time=end_time,
            updated_at=updated_time,
        ),
    ]

    db = make_db_session(sessions)

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_failed_sessions(limit=10)

    assert len(result) == 2

    assert result[0]["session_id"] == "failed_1"
    assert result[0]["candidate_id"] == "candidate_1"
    assert result[0]["status"] == "FAILED"
    assert result[0]["risk_score"] == 0.4
    assert result[0]["assigned_node"] == "worker-1"
    assert result[0]["start_time"] == start_time.isoformat()
    assert result[0]["end_time"] == end_time.isoformat()
    assert result[0]["updated_at"] == updated_time.isoformat()

    assert result[1]["session_id"] == "timeout_1"
    assert result[1]["status"] == "TIMEOUT"
    assert result[1]["assigned_node"] is None

    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_active_sessions_filters_by_status(tracker):
    session = make_interview(
        session_id="queued_1",
        candidate_id="candidate_1",
        status="QUEUED",
    )

    db = make_db_session([session])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_active_sessions(status="queued")

    assert len(result) == 1
    assert result[0]["session_id"] == "queued_1"
    assert result[0]["status"] == "QUEUED"

    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_active_sessions_accepts_iso_since_filter(tracker):
    since = datetime.now(timezone.utc) - timedelta(minutes=30)

    session = make_interview(
        session_id="recent_1",
        candidate_id="candidate_1",
        status="PROCESSING",
        start_time=datetime.now(timezone.utc),
    )

    db = make_db_session([session])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_active_sessions(since=since.isoformat())

    assert len(result) == 1
    assert result[0]["session_id"] == "recent_1"
    assert result[0]["status"] == "PROCESSING"

    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_active_sessions_rejects_invalid_since(tracker):
    db = make_db_session([])

    with (
        patch.object(st_module, "SessionLocal", return_value=db),
        pytest.raises(ValueError, match="Invalid ISO datetime format"),
    ):
        tracker.get_active_sessions(since="not-a-valid-datetime")

    db.execute.assert_not_called()
    db.close.assert_called_once()


def test_get_high_risk_sessions_returns_empty_list_when_none_match(tracker):
    db = make_db_session([])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_high_risk_sessions(threshold=0.8, limit=10)

    assert result == []
    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_stuck_sessions_returns_empty_list_when_none_are_stuck(tracker):
    db = make_db_session([])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_stuck_sessions(timeout_minutes=30)

    assert result == []
    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_worker_distribution_returns_empty_dict_when_no_active_sessions(tracker):
    db = make_db_session([])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_worker_distribution()

    assert result == {}
    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_failed_sessions_returns_empty_list_when_none_exist(tracker):
    db = make_db_session([])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_failed_sessions(limit=10)

    assert result == []
    db.execute.assert_called_once()
    db.close.assert_called_once()


def test_get_active_sessions_returns_expected_fields(tracker):
    start_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    updated_at = datetime.now(timezone.utc)

    session = make_interview(
        session_id="active_1",
        candidate_id="candidate_1",
        status="PROCESSING",
        assigned_node="worker-1",
        start_time=start_time,
        created_at=created_at,
        updated_at=updated_at,
    )

    db = make_db_session([session])

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_active_sessions()

    assert result == [
        {
            "session_id": "active_1",
            "candidate_id": "candidate_1",
            "status": "PROCESSING",
            "assigned_node": "worker-1",
            "start_time": start_time.isoformat(),
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }
    ]

    db.close.assert_called_once()


def test_get_high_risk_sessions_returns_sorted_matching_sessions(tracker):
    sessions = [
        make_interview(
            session_id="risk_low",
            candidate_id="candidate_1",
            status="COMPLETED",
            risk_score=0.85,
            end_time=datetime.now(timezone.utc),
        ),
        make_interview(
            session_id="risk_high",
            candidate_id="candidate_2",
            status="COMPLETED",
            risk_score=0.95,
            end_time=datetime.now(timezone.utc),
        ),
    ]

    db = make_db_session(sessions)

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_high_risk_sessions(threshold=0.8, limit=10)

    assert len(result) == 2
    assert result[0]["session_id"] == "risk_low"
    assert result[0]["risk_score"] == 0.85
    assert result[0]["status"] == "COMPLETED"
    assert result[0]["completed_at"] is not None

    assert result[1]["session_id"] == "risk_high"
    assert result[1]["risk_score"] == 0.95

    db.close.assert_called_once()


def test_get_completed_sessions_returns_empty_list_on_db_error(tracker):
    db = MagicMock()
    db.execute.side_effect = RuntimeError("database unavailable")

    with patch.object(st_module, "SessionLocal", return_value=db):
        result = tracker.get_completed_sessions()

    assert result == []
    db.close.assert_called_once()
