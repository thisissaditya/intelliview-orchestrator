from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.session_control import (
    MAX_RETRIES,
    UNANSWERED_DEDUCTION,
    _calculate_partial_score,
    create_session_control_router,
    has_pending_retry,
    increment_retry_count,
    mark_retry_pending,
)


def test_partial_score_uses_answered_questions_only():
    questions = [
        {"question_id": "q1"},
        {"question_id": "q2"},
        {"question_id": "q3"},
        {"question_id": "q4"},
    ]

    answers = [
        {"question_id": "q1", "score": 8.0},
        {"question_id": "q2", "score": 6.0},
    ]

    score, answered, unanswered, deduction = _calculate_partial_score(
        questions,
        answers,
    )

    assert answered == 2
    assert unanswered == 2
    assert deduction == 10.0

    # Average = 7.0
    # Two unanswered questions = 10% deduction
    assert score == pytest.approx(6.3)


def test_partial_score_applies_five_percent_per_unanswered_question():
    questions = [
        {"question_id": "q1"},
        {"question_id": "q2"},
        {"question_id": "q3"},
    ]

    answers = [
        {"question_id": "q1", "score": 10.0},
        {"question_id": "q2", "score": 10.0},
    ]

    score, answered, unanswered, deduction = _calculate_partial_score(
        questions,
        answers,
    )

    assert answered == 2
    assert unanswered == 1
    assert deduction == UNANSWERED_DEDUCTION * 100
    assert score == pytest.approx(9.5)


def test_partial_score_ignores_answers_without_scores():
    questions = [
        {"question_id": "q1"},
        {"question_id": "q2"},
    ]

    answers = [
        {"question_id": "q1", "score": 8.0},
        {"question_id": "q2", "score": None},
    ]

    score, answered, unanswered, _ = _calculate_partial_score(
        questions,
        answers,
    )

    assert answered == 1
    assert unanswered == 1
    assert score == pytest.approx(7.6)


def test_partial_score_with_no_answered_questions():
    questions = [
        {"question_id": "q1"},
        {"question_id": "q2"},
    ]

    score, answered, unanswered, deduction = _calculate_partial_score(
        questions,
        [],
    )

    assert score == 0.0
    assert answered == 0
    assert unanswered == 2
    assert deduction == 10.0


def test_retry_limit_is_one():
    assert MAX_RETRIES == 1


def test_retry_pending_is_tracked_by_candidate_and_role():
    """Retry eligibility is isolated by candidate and role."""
    redis_client = MagicMock()

    redis_client.get.return_value = None

    assert not has_pending_retry(
        redis_client,
        "candidate-1",
        "Python Developer",
    )

    mark_retry_pending(
        redis_client,
        "candidate-1",
        "Python Developer",
    )

    redis_client.get.return_value = b"1"

    assert has_pending_retry(
        redis_client,
        "candidate-1",
        "Python Developer",
    )

    redis_client.get.return_value = None

    assert not has_pending_retry(
        redis_client,
        "candidate-2",
        "Python Developer",
    )

    assert not has_pending_retry(
        redis_client,
        "candidate-1",
        "Java Developer",
    )


def test_retry_count_can_be_incremented():
    """A retry attempt increments the candidate-role counter."""
    redis_client = MagicMock()
    redis_client.incr.return_value = 1

    count = increment_retry_count(
        redis_client,
        "candidate-1",
        "Python Developer",
    )

    assert count == 1

    redis_client.incr.assert_called_once_with(
        "interview_retry:candidate-1:python developer"
    )


def test_end_interview_marks_retry_pending(
    mock_db_session,
):
    """Ending an active interview makes one retry available."""
    session_manager = MagicMock()
    redis_client = MagicMock()

    session_manager.get_session.return_value = {
        "session_id": "session-72",
        "candidate_id": "candidate-72",
        "position": "Python Developer",
        "status": "PROCESSING",
        "questions_asked": [
            {"question_id": "q1"},
            {"question_id": "q2"},
        ],
        "answers_provided": [
            {"question_id": "q1", "score": 8.0},
        ],
    }

    interview = MagicMock()
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = interview

    app = FastAPI()

    app.include_router(
        create_session_control_router(
            session_manager=session_manager,
            redis_client=redis_client,
        )
    )

    client = TestClient(app)

    with patch(
        "routers.session_control.mark_retry_pending",
        return_value=True,
    ) as mock_mark_retry:
        response = client.post("/sessions/session-72/end")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["partial_score"] == pytest.approx(7.6)
    assert data["answered_questions"] == 1
    assert data["unanswered_questions"] == 1
    assert data["deduction_percent"] == 5.0

    mock_mark_retry.assert_called_once_with(
        redis_client,
        "candidate-72",
        "Python Developer",
    )

    assert interview.status == "COMPLETED"
    assert interview.overall_score == pytest.approx(7.6)

    mock_db_session.commit.assert_called_once()


def test_start_interview_rejects_retry_after_limit():
    """A second retry for the same candidate and role is rejected."""

    from fastapi import HTTPException

    from orchestrator.main import start_interview
    from routers.sessions import StartInterviewRequest

    request = StartInterviewRequest(
        candidate_id="candidate-72",
        candidate_name="Test Candidate",
        position="Python Developer",
        priority="medium",
    )

    redis_client = MagicMock()

    scheduler_mock = MagicMock()
    scheduler_mock.can_accept_task.return_value = True

    with (
        patch(
            "orchestrator.main.scheduler",
            scheduler_mock,
        ),
        patch(
            "orchestrator.main.get_redis_client",
            return_value=redis_client,
        ),
        patch(
            "orchestrator.main.get_retry_count",
            return_value=MAX_RETRIES,
        ),
        patch(
            "orchestrator.main.has_pending_retry",
            return_value=True,
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(
                start_interview(
                    request=request,
                    session_db=MagicMock(),
                )
            )

    assert exc_info.value.status_code == 409
    assert "Retry limit reached" in exc_info.value.detail
    assert "candidate-72" in exc_info.value.detail
    assert "Python Developer" in exc_info.value.detail


@pytest.mark.asyncio
async def test_start_interview_allows_first_retry():
    """The first retry is allowed and consumes the pending retry."""
    from orchestrator.main import start_interview
    from routers.sessions import StartInterviewRequest

    request = StartInterviewRequest(
        candidate_id="candidate-72",
        candidate_name="Test Candidate",
        position="Python Developer",
        priority="medium",
    )

    redis_client = MagicMock()

    session_manager = MagicMock()
    session_manager.QUEUED = "QUEUED"
    session_manager.create_session.return_value = "retry-session-1"
    session_manager.get_session.return_value = {
        "session_id": "retry-session-1",
        "created_at": "2026-08-26T12:00:00+00:00",
    }

    scheduler = MagicMock()
    scheduler.can_accept_task.return_value = True
    scheduler.get_estimated_wait_time.return_value = 0

    with (
        patch(
            "orchestrator.main.get_redis_client",
            return_value=redis_client,
        ),
        patch(
            "orchestrator.main.get_retry_count",
            return_value=0,
        ),
        patch(
            "orchestrator.main.has_pending_retry",
            return_value=True,
        ),
        patch(
            "orchestrator.main.consume_retry",
            return_value=True,
        ) as mock_consume_retry,
        patch(
            "orchestrator.main.session_manager",
            session_manager,
        ),
        patch(
            "orchestrator.main.scheduler",
            scheduler,
        ),
        patch(
            "orchestrator.main.http_cache.invalidate",
        ),
        patch(
            "orchestrator.main.SESSIONS_CREATED.inc",
        ),
        patch(
            "orchestrator.main.SESSIONS_ACTIVE.inc",
        ),
    ):
        response = await start_interview(
            request=request,
            session_db=MagicMock(),
        )

    assert response.session_id == "retry-session-1"
    assert response.status == "QUEUED"

    mock_consume_retry.assert_called_once_with(
        redis_client,
        "candidate-72",
        "Python Developer",
    )

    session_manager.create_session.assert_called_once_with(
        candidate_id="candidate-72",
        candidate_name="Test Candidate",
        position="Python Developer",
    )

    scheduler.schedule_task.assert_called_once()
