"""Backend controls for early interview termination and retry limits."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from database import db
from database.models import InterviewSession

UNANSWERED_DEDUCTION = 0.05
MAX_RETRIES = 1

ACTIVE_STATUSES = {
    "CREATED",
    "QUEUED",
    "PROCESSING",
    "VIDEO_PROCESSING",
    "AUDIO_PROCESSING",
    "EVALUATING",
}

RETRY_COUNT_KEY_PREFIX = "interview_retry:"
RETRY_PENDING_KEY_PREFIX = "interview_retry_pending:"
RETRY_COUNT_TTL = 604800  # 7 days


class EndInterviewResponse(BaseModel):
    """Response returned after an interview is ended early."""

    session_id: str
    status: str
    partial_score: float
    answered_questions: int
    unanswered_questions: int
    deduction_percent: float


class RetryLimitResponse(BaseModel):
    """Response information for retry-limit checks."""

    candidate_id: str
    position: str
    retry_count: int
    max_retries: int
    can_retry: bool


def _calculate_partial_score(
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
) -> tuple[float, int, int, float]:
    """
    Calculate the partial score for an early-ended interview.

    Only answers that contain a score contribute to the average.
    Each unanswered question causes a 5% deduction from that average.
    """
    answered_scores = [
        answer["score"] for answer in answers if answer.get("score") is not None
    ]

    answered_count = len(answered_scores)
    unanswered_count = max(len(questions) - answered_count, 0)

    if not answered_scores:
        deduction_percent = min(
            unanswered_count * UNANSWERED_DEDUCTION * 100,
            100.0,
        )
        return 0.0, 0, unanswered_count, deduction_percent

    average_score = sum(answered_scores) / answered_count

    deduction = min(
        unanswered_count * UNANSWERED_DEDUCTION,
        1.0,
    )

    partial_score = max(
        average_score * (1.0 - deduction),
        0.0,
    )

    return (
        round(partial_score, 3),
        answered_count,
        unanswered_count,
        round(deduction * 100, 2),
    )


def _retry_key(candidate_id: str, position: str) -> str:
    """Build the retry counter key for a candidate and role."""
    normalized_position = position.strip().lower()

    return f"{RETRY_COUNT_KEY_PREFIX}" f"{candidate_id}:" f"{normalized_position}"


def _retry_pending_key(candidate_id: str, position: str) -> str:
    """Build the pending-retry key for a candidate and role."""
    normalized_position = position.strip().lower()

    return f"{RETRY_PENDING_KEY_PREFIX}" f"{candidate_id}:" f"{normalized_position}"


def get_retry_count(
    redis_client: Any,
    candidate_id: str,
    position: str,
) -> int:
    """Return the current retry count for a candidate and role."""
    if redis_client is None:
        return 0

    value = redis_client.get(_retry_key(candidate_id, position))

    if value is None:
        return 0

    return int(value)


def has_pending_retry(
    redis_client: Any,
    candidate_id: str,
    position: str,
) -> bool:
    """Return whether an early-ended interview has a retry available."""
    if redis_client is None:
        return False

    return bool(
        redis_client.get(
            _retry_pending_key(
                candidate_id,
                position,
            )
        )
    )


def mark_retry_pending(
    redis_client: Any,
    candidate_id: str,
    position: str,
) -> bool:
    """Mark a candidate-role pair as eligible for a retry."""
    if redis_client is None:
        return False

    redis_client.set(
        _retry_pending_key(
            candidate_id,
            position,
        ),
        "1",
        ex=RETRY_COUNT_TTL,
    )

    return True


def increment_retry_count(
    redis_client: Any,
    candidate_id: str,
    position: str,
) -> int:
    """Increment the retry count for a candidate and role."""
    if redis_client is None:
        return 1

    key = _retry_key(candidate_id, position)

    count = int(redis_client.incr(key))

    if hasattr(redis_client, "expire"):
        redis_client.expire(
            key,
            RETRY_COUNT_TTL,
        )

    return count


def can_retry(
    redis_client: Any,
    candidate_id: str,
    position: str,
) -> bool:
    """Return whether another retry is available."""
    return (
        get_retry_count(
            redis_client,
            candidate_id,
            position,
        )
        < MAX_RETRIES
    )


def consume_retry(
    redis_client: Any,
    candidate_id: str,
    position: str,
) -> bool:
    """Consume one available retry for a candidate and role."""
    if not has_pending_retry(
        redis_client,
        candidate_id,
        position,
    ):
        return False

    if not can_retry(
        redis_client,
        candidate_id,
        position,
    ):
        return False

    increment_retry_count(
        redis_client,
        candidate_id,
        position,
    )

    redis_client.delete(
        _retry_pending_key(
            candidate_id,
            position,
        )
    )

    return True


def create_session_control_router(
    session_manager,
    redis_client,
) -> APIRouter:
    """Create interview session-control routes."""

    router = APIRouter(
        prefix="/sessions",
        tags=["session-control"],
    )

    @router.post(
        "/{session_id}/end",
        response_model=EndInterviewResponse,
    )
    async def end_interview(
        session_id: str,
    ) -> EndInterviewResponse:
        """End an active interview and calculate its partial score."""

        session_data = session_manager.get_session(session_id)

        if not session_data:
            raise HTTPException(
                status_code=404,
                detail="Interview session not found",
            )

        current_status = session_data.get("status")

        if current_status not in ACTIVE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Interview session is not active",
            )
        candidate_id = session_data.get("candidate_id")
        position = (session_data.get("position") or "").strip()

        questions = session_data.get(
            "questions_asked",
            [],
        )

        answers = session_data.get(
            "answers_provided",
            [],
        )

        (
            partial_score,
            answered_count,
            unanswered_count,
            deduction_percent,
        ) = _calculate_partial_score(
            questions,
            answers,
        )

        session_db = db.SessionLocal()

        try:
            interview = session_db.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()

            if not interview:
                raise HTTPException(
                    status_code=404,
                    detail="Interview session not found",
                )

            interview.status = "COMPLETED"
            interview.overall_score = partial_score
            interview.end_time = datetime.now(timezone.utc)

            session_db.commit()

            if candidate_id and position:
                mark_retry_pending(
                    redis_client,
                    candidate_id,
                    position,
                )

        except HTTPException:
            session_db.rollback()
            raise

        except Exception as exc:
            session_db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to end interview",
            ) from exc

        finally:
            session_db.close()

        session_data["status"] = "COMPLETED"
        session_data["overall_score"] = partial_score
        session_data["partial_score"] = partial_score
        session_data["answered_questions"] = answered_count
        session_data["unanswered_questions"] = unanswered_count

        if hasattr(
            session_manager,
            "state_sync",
        ):
            session_manager.state_sync.set_session_state(
                session_id,
                session_data,
            )

        return EndInterviewResponse(
            session_id=session_id,
            status="COMPLETED",
            partial_score=partial_score,
            answered_questions=answered_count,
            unanswered_questions=unanswered_count,
            deduction_percent=deduction_percent,
        )

    return router
