"""
Unit tests for orchestrator.session_manager.SessionManager

These tests mock out every external dependency (Postgres via SessionLocal,
Redis via StateSynchronizer, the circuit breaker, and the WebSocket
broadcaster) so they run in isolation and don't need a live DB/Redis.

Run with:
    pytest test_session_manager.py -v
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import orchestrator.session_manager as sm_module
from orchestrator.session_manager import SessionManager

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager():
    """A SessionManager with its StateSynchronizer swapped for a mock."""
    with patch.object(sm_module, "StateSynchronizer"):
        mgr = SessionManager()
    mgr.state_sync = MagicMock()
    return mgr


def make_interview(status, **overrides):
    """Stand-in for an InterviewSession ORM row returned by a query."""
    interview = MagicMock()
    interview.status = status
    interview.risk_score = overrides.get("risk_score")
    interview.session_id = overrides.get("session_id", "session_abc123")
    interview.candidate_id = overrides.get("candidate_id", "cand_1")
    interview.assigned_node = overrides.get("assigned_node")
    interview.start_time = overrides.get("start_time")
    interview.end_time = overrides.get("end_time")
    interview.created_at = overrides.get("created_at")
    interview.updated_at = overrides.get("updated_at")
    interview.video_analysis = overrides.get("video_analysis")
    interview.audio_analysis = overrides.get("audio_analysis")
    interview.evaluation_analysis = overrides.get("evaluation_analysis")
    return interview


def make_db_session(scalar_result=None):
    """Stand-in for the Session object returned by SessionLocal()."""
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = scalar_result
    db.execute.return_value = execute_result
    return db


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_creates_db_record_and_syncs_redis(self, manager):
        existing_candidate = MagicMock()  # candidate already exists → skip auto-create
        db = make_db_session(scalar_result=existing_candidate)
        with patch.object(sm_module, "SessionLocal", return_value=db):
            session_id = manager.create_session(
                candidate_id="cand_1",
                position="Backend Engineer",
                candidate_name="Asha",
            )

        assert session_id.startswith("session_")
        db.add.assert_called_once()
        added_record = db.add.call_args[0][0]
        assert added_record.session_id == session_id
        assert added_record.candidate_id == "cand_1"
        assert added_record.status == SessionManager.CREATED
        db.commit.assert_called_once()
        db.close.assert_called_once()

        manager.state_sync.set_session_state.assert_called_once()
        synced_id, synced_data = manager.state_sync.set_session_state.call_args[0]
        assert synced_id == session_id
        assert synced_data["status"] == SessionManager.CREATED
        assert synced_data["candidate_id"] == "cand_1"
        assert synced_data["position"] == "Backend Engineer"
        assert synced_data["candidate_name"] == "Asha"
        assert synced_data["risk_score"] is None

    def test_auto_creates_missing_candidate(self, manager):
        # candidate lookup returns None → should auto-create a candidate
        # record before creating the interview session
        db = make_db_session(scalar_result=None)
        with patch.object(sm_module, "SessionLocal", return_value=db):
            manager.create_session(candidate_id="cand_new", candidate_name="Riya")

        assert db.add.call_count == 2
        added_records = [call.args[0] for call in db.add.call_args_list]
        assert added_records[0].candidate_id == "cand_new"
        assert added_records[0].name == "Riya"
        assert added_records[1].candidate_id == "cand_new"
        db.flush.assert_called_once()

    def test_defaults_position_and_name_when_omitted(self, manager):
        db = make_db_session()
        with patch.object(sm_module, "SessionLocal", return_value=db):
            manager.create_session(candidate_id="cand_2")

        synced_data = manager.state_sync.set_session_state.call_args[0][1]
        assert synced_data["candidate_name"] == "Unknown"
        assert synced_data["position"] == "Unknown"

    def test_rolls_back_and_reraises_on_db_error(self, manager):
        db = make_db_session()
        db.commit.side_effect = RuntimeError("db unavailable")
        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            pytest.raises(RuntimeError),
        ):
            manager.create_session(candidate_id="cand_3")

        db.rollback.assert_called_once()
        db.close.assert_called_once()
        manager.state_sync.set_session_state.assert_not_called()

    def test_generates_unique_session_ids(self, manager):
        db = make_db_session()
        with patch.object(sm_module, "SessionLocal", return_value=db):
            ids = {manager.create_session(candidate_id="cand_x") for _ in range(50)}
        assert len(ids) == 50


# ---------------------------------------------------------------------------
# update_session_status — the core transition machine
# ---------------------------------------------------------------------------


class TestUpdateSessionStatus:
    def test_valid_transition_updates_db_and_redis(self, manager):
        interview = make_interview(SessionManager.CREATED)
        db = make_db_session(scalar_result=interview)
        manager.state_sync.get_session_state.return_value = {
            "status": SessionManager.CREATED
        }

        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            patch.object(sm_module, "is_circuit_open", return_value=False),
        ):
            result = manager.update_session_status(
                "session_abc123", SessionManager.QUEUED
            )

        assert result is True
        assert interview.status == SessionManager.QUEUED
        db.commit.assert_called_once()
        manager.state_sync.set_session_state.assert_called_once()
        pushed_data = manager.state_sync.set_session_state.call_args[0][1]
        assert pushed_data["status"] == SessionManager.QUEUED

    def test_merges_metadata_into_redis_payload(self, manager):
        interview = make_interview(SessionManager.QUEUED)
        db = make_db_session(scalar_result=interview)
        manager.state_sync.get_session_state.return_value = {
            "status": SessionManager.QUEUED
        }

        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            patch.object(sm_module, "is_circuit_open", return_value=False),
        ):
            manager.update_session_status(
                "session_abc123",
                SessionManager.PROCESSING,
                metadata={"worker": "node-3"},
            )

        pushed_data = manager.state_sync.set_session_state.call_args[0][1]
        assert pushed_data["worker"] == "node-3"

    def test_invalid_transition_is_rejected(self, manager):
        # COMPLETED has no valid outbound transitions.
        interview = make_interview(SessionManager.COMPLETED)
        db = make_db_session(scalar_result=interview)

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.update_session_status(
                "session_abc123", SessionManager.QUEUED
            )

        assert result is False
        assert interview.status == SessionManager.COMPLETED  # unchanged
        db.commit.assert_not_called()
        manager.state_sync.set_session_state.assert_not_called()

    def test_unknown_current_status_is_rejected(self, manager):
        interview = make_interview("SOME_UNKNOWN_STATE")
        db = make_db_session(scalar_result=interview)

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.update_session_status(
                "session_abc123", SessionManager.QUEUED
            )

        assert result is False
        db.commit.assert_not_called()

    def test_session_not_found_returns_false(self, manager):
        db = make_db_session(scalar_result=None)
        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.update_session_status(
                "does_not_exist", SessionManager.QUEUED
            )

        assert result is False
        db.commit.assert_not_called()

    def test_skips_redis_sync_when_circuit_breaker_open(self, manager):
        interview = make_interview(SessionManager.CREATED)
        db = make_db_session(scalar_result=interview)

        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            patch.object(sm_module, "is_circuit_open", return_value=True),
        ):
            result = manager.update_session_status(
                "session_abc123", SessionManager.QUEUED
            )

        assert result is True  # DB write still succeeds
        assert interview.status == SessionManager.QUEUED
        manager.state_sync.get_session_state.assert_not_called()
        manager.state_sync.set_session_state.assert_not_called()

    def test_db_error_rolls_back_and_returns_false(self, manager):
        interview = make_interview(SessionManager.CREATED)
        db = make_db_session(scalar_result=interview)
        db.commit.side_effect = RuntimeError("db unavailable")

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.update_session_status(
                "session_abc123", SessionManager.QUEUED
            )

        assert result is False
        db.rollback.assert_called_once()

    def test_broadcasts_update_when_event_loop_is_running(self, manager):
        interview = make_interview(SessionManager.CREATED)
        db = make_db_session(scalar_result=interview)
        manager.state_sync.get_session_state.return_value = {
            "status": SessionManager.CREATED
        }

        async def scenario():
            with (
                patch.object(sm_module, "SessionLocal", return_value=db),
                patch.object(sm_module, "is_circuit_open", return_value=False),
                patch.object(sm_module, "ws_manager") as mock_ws,
            ):
                mock_ws.broadcast_session_update = AsyncMock()
                manager.update_session_status(
                    "session_abc123", SessionManager.QUEUED, metadata={"note": "ok"}
                )
                await asyncio.sleep(0)  # let the fire-and-forget task run
                mock_ws.broadcast_session_update.assert_awaited_once_with(
                    session_id="session_abc123",
                    status=SessionManager.QUEUED,
                    details={"note": "ok"},
                    risk_score=interview.risk_score,
                )

        asyncio.run(scenario())


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------


class TestGetSession:
    def test_returns_cached_value_without_hitting_db(self, manager):
        manager.state_sync.get_session_state.return_value = {
            "session_id": "session_abc123"
        }

        with patch.object(sm_module, "SessionLocal") as mock_session_local:
            result = manager.get_session("session_abc123")

        assert result == {"session_id": "session_abc123"}
        mock_session_local.assert_not_called()

    def test_falls_back_to_db_and_repopulates_cache(self, manager):
        manager.state_sync.get_session_state.return_value = None
        interview = make_interview(SessionManager.EVALUATING, risk_score=0.42)
        db = make_db_session(scalar_result=interview)

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.get_session("session_abc123")

        assert result["session_id"] == "session_abc123"
        assert result["status"] == SessionManager.EVALUATING
        assert result["risk_score"] == 0.42
        manager.state_sync.set_session_state.assert_called_once_with(
            "session_abc123", result
        )
        db.close.assert_called_once()

    def test_returns_none_when_not_found_anywhere(self, manager):
        manager.state_sync.get_session_state.return_value = None
        db = make_db_session(scalar_result=None)

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.get_session("does_not_exist")

        assert result is None
        manager.state_sync.set_session_state.assert_not_called()

    def test_returns_none_when_db_lookup_raises(self, manager):
        manager.state_sync.get_session_state.return_value = None
        db = make_db_session()
        db.execute.side_effect = RuntimeError("db unavailable")

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.get_session("session_abc123")

        assert result is None
        db.rollback.assert_called_once()
        db.close.assert_called_once()

    def test_cache_lookup_error_returns_none(self, manager):
        """
        Redis/cache failure should be handled gracefully without
        raising UnboundLocalError.
        """
        manager.state_sync.get_session_state.side_effect = RuntimeError("redis down")

        result = manager.get_session("session_abc123")

        assert result is None


# ---------------------------------------------------------------------------
# mark_session_failed
# ---------------------------------------------------------------------------


class TestMarkSessionFailed:
    def test_delegates_to_update_session_status_with_failed(self, manager):
        with patch.object(
            manager, "update_session_status", return_value=True
        ) as mock_update:
            result = manager.mark_session_failed("session_abc123", "video decode error")

        assert result is True
        mock_update.assert_called_once_with(
            "session_abc123",
            SessionManager.FAILED,
            {"error_message": "video decode error"},
        )

    def test_propagates_false_from_update(self, manager):
        with patch.object(manager, "update_session_status", return_value=False):
            result = manager.mark_session_failed("session_abc123", "boom")

        assert result is False


# ---------------------------------------------------------------------------
# mark_session_completed
# ---------------------------------------------------------------------------


class TestMarkSessionCompleted:
    def test_marks_completed_and_syncs_redis(self, manager):
        interview = make_interview(SessionManager.EVALUATING)
        db = make_db_session(scalar_result=interview)
        manager.state_sync.get_session_state.return_value = {
            "status": SessionManager.EVALUATING
        }

        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            patch.object(sm_module, "is_circuit_open", return_value=False),
        ):
            result = manager.mark_session_completed("session_abc123", risk_score=0.87)

        assert result is True
        assert interview.status == SessionManager.COMPLETED
        assert interview.risk_score == 0.87
        assert interview.end_time is not None
        db.commit.assert_called_once()

        pushed_data = manager.state_sync.set_session_state.call_args[0][1]
        assert pushed_data["status"] == SessionManager.COMPLETED
        assert pushed_data["risk_score"] == 0.87

    def test_skips_redis_sync_when_circuit_breaker_open(self, manager):
        interview = make_interview(SessionManager.EVALUATING)
        db = make_db_session(scalar_result=interview)

        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            patch.object(sm_module, "is_circuit_open", return_value=True),
        ):
            result = manager.mark_session_completed("session_abc123", risk_score=0.1)

        assert result is True
        manager.state_sync.set_session_state.assert_not_called()

    def test_session_not_found_returns_false(self, manager):
        db = make_db_session(scalar_result=None)
        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.mark_session_completed("does_not_exist", risk_score=0.5)

        assert result is False
        db.commit.assert_not_called()

    def test_rejects_invalid_transition_to_completed(self, manager):
        interview = make_interview(SessionManager.CREATED)
        db = make_db_session(scalar_result=interview)

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.mark_session_completed(
                "session_abc123",
                risk_score=0.5,
            )

        assert result is False
        assert interview.status == SessionManager.CREATED
        db.commit.assert_not_called()
        manager.state_sync.set_session_state.assert_not_called()

    def test_db_error_rolls_back_and_returns_false(self, manager):
        interview = make_interview(SessionManager.EVALUATING)
        db = make_db_session(scalar_result=interview)
        db.commit.side_effect = RuntimeError("db unavailable")

        with patch.object(sm_module, "SessionLocal", return_value=db):
            result = manager.mark_session_completed("session_abc123", risk_score=0.5)

        assert result is False
        db.rollback.assert_called_once()

    def test_no_redis_update_when_no_cached_state_exists(self, manager):
        # get_session_state() returning falsy means the "if session_data:"
        # guard skips set_session_state entirely, even with circuit closed.
        interview = make_interview(SessionManager.EVALUATING)
        db = make_db_session(scalar_result=interview)
        manager.state_sync.get_session_state.return_value = None

        with (
            patch.object(sm_module, "SessionLocal", return_value=db),
            patch.object(sm_module, "is_circuit_open", return_value=False),
        ):
            result = manager.mark_session_completed("session_abc123", risk_score=0.5)

        assert result is True
        manager.state_sync.set_session_state.assert_not_called()


# ---------------------------------------------------------------------------
# _is_valid_transition — exhaustive coverage of the state machine
# ---------------------------------------------------------------------------


class TestIsValidTransition:
    @pytest.mark.parametrize(
        "current,new",
        [
            (SessionManager.CREATED, SessionManager.QUEUED),
            (SessionManager.QUEUED, SessionManager.PROCESSING),
            (SessionManager.QUEUED, SessionManager.VIDEO_PROCESSING),
            (SessionManager.PROCESSING, SessionManager.VIDEO_PROCESSING),
            (SessionManager.PROCESSING, SessionManager.COMPLETED),
            (SessionManager.VIDEO_PROCESSING, SessionManager.AUDIO_PROCESSING),
            (SessionManager.AUDIO_PROCESSING, SessionManager.EVALUATING),
            (SessionManager.EVALUATING, SessionManager.COMPLETED),
            (SessionManager.TIMEOUT, SessionManager.FAILED),
        ],
    )
    def test_valid_transitions_allowed(self, manager, current, new):
        assert manager._is_valid_transition(current, new) is True

    @pytest.mark.parametrize(
        "current,new",
        [
            (SessionManager.COMPLETED, SessionManager.QUEUED),
            (SessionManager.FAILED, SessionManager.PROCESSING),
            (SessionManager.CANCELLED, SessionManager.CREATED),
            (SessionManager.CREATED, SessionManager.COMPLETED),  # skips the pipeline
            (SessionManager.TIMEOUT, SessionManager.COMPLETED),
            ("NOT_A_REAL_STATE", SessionManager.QUEUED),  # unknown current state
        ],
    )
    def test_invalid_transitions_rejected(self, manager, current, new):
        assert manager._is_valid_transition(current, new) is False

    def test_terminal_states_have_no_outbound_transitions(self, manager):
        for terminal in (
            SessionManager.COMPLETED,
            SessionManager.FAILED,
            SessionManager.CANCELLED,
        ):
            assert SessionManager.VALID_TRANSITIONS[terminal] == []


# ---------------------------------------------------------------------------
# _broadcast_status — fire-and-forget WebSocket emission
# ---------------------------------------------------------------------------


class TestBroadcastStatus:
    def test_noop_when_no_event_loop_is_running(self):
        # Called from plain sync code (no running loop) -> must not raise.
        SessionManager._broadcast_status(
            "session_abc123", SessionManager.QUEUED, None, {}
        )

    def test_schedules_broadcast_when_loop_is_running(self):
        async def scenario():
            with patch.object(sm_module, "ws_manager") as mock_ws:
                mock_ws.broadcast_session_update = AsyncMock()
                SessionManager._broadcast_status(
                    "session_abc123", SessionManager.EVALUATING, 0.5, {"k": "v"}
                )
                await asyncio.sleep(0)
                mock_ws.broadcast_session_update.assert_awaited_once_with(
                    session_id="session_abc123",
                    status=SessionManager.EVALUATING,
                    details={"k": "v"},
                    risk_score=0.5,
                )

        asyncio.run(scenario())

    def test_broadcast_failure_is_swallowed_not_raised(self):
        async def scenario():
            with patch.object(sm_module, "ws_manager") as mock_ws:
                mock_ws.broadcast_session_update = AsyncMock(
                    side_effect=RuntimeError("ws down")
                )
                SessionManager._broadcast_status(
                    "session_abc123", SessionManager.FAILED, None, {}
                )
                # Should not raise even though the underlying broadcast failed.
                await asyncio.sleep(0)

        asyncio.run(scenario())  # completing without raising is the assertion


@pytest.mark.asyncio
async def test_question_timer_calls_timeout(manager):
    callback = AsyncMock()

    manager.QUESTION_ANSWER_TIMEOUT = 0.01

    manager.start_question_timer(
        "session_1",
        "question_1",
        callback,
    )

    await asyncio.sleep(0.02)

    callback.assert_awaited_once_with("session_1", "question_1")


@pytest.mark.asyncio
async def test_question_timer_can_be_cancelled(manager):
    callback = AsyncMock()

    manager.QUESTION_ANSWER_TIMEOUT = 0.01

    manager.start_question_timer(
        "session_1",
        "question_1",
        callback,
    )

    manager.cancel_question_timer("session_1", "question_1")

    await asyncio.sleep(0.02)

    callback.assert_not_awaited()
