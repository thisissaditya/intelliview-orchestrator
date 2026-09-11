"""Anti-cheat integrity signal ingestion routes."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from workers.integrity_score import IntegrityScorer

router = APIRouter(prefix="/integrity", tags=["integrity"])


# In-memory storage of integrity events grouped by session_id.
integrity_events: dict[str, list[dict[str, Any]]] = {}

# Latest fused integrity score for each session.
# Score is produced by the existing Task D IntegrityScorer.
integrity_scores: dict[str, int] = {}
# Event-type values that count as a browser tab switch for integrity scoring.
_TAB_SWITCH_EVENT_TYPES = {"tab_switch", "tab_switching", "tab-switch"}


def get_tab_switch_count(session_id: str) -> int:
    """Count stored tab-switch events for a session.

    Used by the session-status API to feed the live integrity-score fusion
    (see ``workers/integrity_score.py``) so the score reflects tab-switch
    signals as soon as they're ingested via ``POST /integrity/events``.
    """
    events = integrity_events.get(session_id, [])
    return sum(
        1
        for e in events
        if e.get("event_type", "").strip().lower() in _TAB_SWITCH_EVENT_TYPES
    )


class IntegrityEvent(BaseModel):
    session_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _calculate_session_integrity_score(session_id: str) -> int:
    """Return the existing Task D integrity score for a session."""

    events = integrity_events.get(session_id, [])

    tab_switches = sum(
        1
        for event in events
        if event["event_type"].lower() in {"tab_switch", "tab-switch", "tabswitch"}
    )

    cv_flags = sum(
        1
        for event in events
        if event["event_type"].lower()
        in {
            "cv_flag",
            "cv-flag",
            "face_flag",
            "face-flag",
            "gaze_flag",
            "gaze-flag",
        }
    )

    # Risk score can be supplied by the event producer when available.
    risk_score = None

    for event in reversed(events):
        metadata = event.get("metadata", {})
        if "risk_score" in metadata:
            try:
                risk_score = float(metadata["risk_score"])
                break
            except (TypeError, ValueError):
                continue

    score = IntegrityScorer.calculate_integrity_score(
        tab_switches=tab_switches,
        cv_flags=cv_flags,
        risk_score=risk_score,
    )

    integrity_scores[session_id] = score
    return score


@router.post("/events")
async def ingest_integrity_event(event: IntegrityEvent):
    """Receive and store an anti-cheat integrity event for a session."""

    stored_event = {
        "session_id": event.session_id,
        "event_type": event.event_type,
        "timestamp": (
            event.timestamp.isoformat()
            if event.timestamp
            else datetime.now(timezone.utc).isoformat()
        ),
        "metadata": event.metadata,
    }

    integrity_events.setdefault(event.session_id, []).append(stored_event)

    score = _calculate_session_integrity_score(event.session_id)

    return {
        "success": True,
        "message": "Integrity event stored",
        "session_id": event.session_id,
        "integrity_score": score,
        "event": stored_event,
    }


@router.get("/events/{session_id}")
async def get_integrity_events(session_id: str):
    """Return all stored integrity events and current score for a session."""

    score = _calculate_session_integrity_score(session_id)

    return {
        "session_id": session_id,
        "integrity_score": score,
        "events": integrity_events.get(session_id, []),
    }


@router.get("/score/{session_id}")
async def get_integrity_score(session_id: str):
    """Return the current Task D fused integrity score for a session."""

    score = _calculate_session_integrity_score(session_id)

    return {
        "session_id": session_id,
        "integrity_score": score,
    }
