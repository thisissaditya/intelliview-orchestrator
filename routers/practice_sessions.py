"""Practice-mode session tracking."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from orchestrator.cache_manager import CacheManager
from orchestrator.security import get_current_user

router = APIRouter(
    prefix="/practice-sessions",
    tags=["Practice Sessions"],
)

PRACTICE_SESSION_KEY = "practice_session:"
PRACTICE_ATTEMPTS_KEY = "practice_attempts:"


class PracticeSessionCreateRequest(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    question_id: str = Field(min_length=1, max_length=128)


class PracticeAttemptRequest(BaseModel):
    answer: str = Field(default="", max_length=10000)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_cache() -> CacheManager:
    return CacheManager()


@router.post("")
async def create_practice_session(
    request: PracticeSessionCreateRequest,
    current_user: Any = Depends(get_current_user),
):
    """Create a separate practice session."""

    practice_session_id = f"practice_{uuid.uuid4().hex[:16]}"

    session_data = {
        "practice_session_id": practice_session_id,
        "candidate_id": request.candidate_id,
        "question_id": request.question_id,
        "created_at": _utcnow(),
        "attempt_count": 0,
    }

    cache = _get_cache()

    cache.set(
        f"{PRACTICE_SESSION_KEY}{practice_session_id}",
        json.dumps(session_data),
    )

    return session_data


@router.post("/{practice_session_id}/attempts")
async def record_practice_attempt(
    practice_session_id: str,
    request: PracticeAttemptRequest,
    current_user: Any = Depends(get_current_user),
):
    """Record a practice attempt without affecting real retry_count."""

    cache = _get_cache()

    session_key = f"{PRACTICE_SESSION_KEY}{practice_session_id}"
    raw_session = cache.get(session_key)

    if not raw_session:
        raise HTTPException(
            status_code=404,
            detail="Practice session not found",
        )

    session_data = json.loads(raw_session)

    attempts_key = f"{PRACTICE_ATTEMPTS_KEY}{practice_session_id}"
    raw_attempts = cache.get(attempts_key)

    attempts = json.loads(raw_attempts) if raw_attempts else []

    attempt = {
        "attempt_id": f"attempt_{uuid.uuid4().hex[:16]}",
        "practice_session_id": practice_session_id,
        "answer": request.answer,
        "created_at": _utcnow(),
    }

    attempts.append(attempt)

    session_data["attempt_count"] = len(attempts)

    cache.set(attempts_key, json.dumps(attempts))
    cache.set(session_key, json.dumps(session_data))

    return {
        "status": "success",
        "practice_session": session_data,
        "attempt": attempt,
    }


@router.get("/{practice_session_id}")
async def get_practice_session(
    practice_session_id: str,
    current_user: Any = Depends(get_current_user),
):
    """Get a practice session and its attempts."""

    cache = _get_cache()

    raw_session = cache.get(f"{PRACTICE_SESSION_KEY}{practice_session_id}")

    if not raw_session:
        raise HTTPException(
            status_code=404,
            detail="Practice session not found",
        )

    raw_attempts = cache.get(f"{PRACTICE_ATTEMPTS_KEY}{practice_session_id}")

    attempts = json.loads(raw_attempts) if raw_attempts else []

    return {
        "practice_session": json.loads(raw_session),
        "attempts": attempts,
    }
