"""Practice session ORM model."""

import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text

from database.models._base import Base, utcnow


def generate_practice_session_id() -> str:
    """Generate unique practice session identifier."""
    return f"practice_{uuid.uuid4().hex[:12]}"


class PracticeSession(Base):
    """Practice interview session tracking."""

    __tablename__ = "practice_sessions"

    session_id = Column(
        String(255),
        primary_key=True,
        default=generate_practice_session_id,
        index=True,
        nullable=False,
    )

    candidate_id = Column(
        String(255),
        ForeignKey("candidates.candidate_id"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="started",
        index=True,
    )

    started_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
    )

    completed_at = Column(
        DateTime,
        nullable=True,
    )

    duration_seconds = Column(
        Float,
        nullable=True,
    )

    score = Column(
        Float,
        nullable=True,
    )

    questions_asked = Column(
        JSON,
        nullable=True,
        default=list,
    )

    answers_provided = Column(
        JSON,
        nullable=True,
        default=list,
    )

    feedback = Column(
        JSON,
        nullable=True,
        default=dict,
    )

    notes = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self):
        return (
            f"<PracticeSession("
            f"session_id='{self.session_id}', "
            f"candidate_id='{self.candidate_id}', "
            f"status='{self.status}')>"
        )
