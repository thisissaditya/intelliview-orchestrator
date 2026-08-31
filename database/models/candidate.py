"""Candidate ORM model."""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from database.models._base import Base, utcnow


class Candidate(Base):
    """Candidate profile"""

    __tablename__ = "candidates"

    candidate_id = Column(String(255), primary_key=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    resume_text = Column(String(10000), nullable=True)
    skills = Column(JSON, nullable=True, default=list)
    interview_history = Column(JSON, nullable=True, default=list)
    demographics = Column(JSON, nullable=True, default=dict)
    avg_score = Column(Float, nullable=True, index=True)
    total_interviews = Column(Integer, nullable=False, default=0, index=True)

    # Verification features
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(50), nullable=True)

    # Streak & Badges features
    practice_streak = Column(Integer, default=0, nullable=False)
    last_practice_date = Column(DateTime(timezone=True), nullable=True)
    badges = Column(JSON, nullable=True, default=list)

    # Search & Filtering status/role
    status = Column(String(50), default="unverified", nullable=True)
    role = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    deleted_at = Column(DateTime, nullable=True, index=True, default=None)

    interview_sessions = relationship("InterviewSession", back_populates="candidate")

    def __repr__(self):
        return f"<Candidate(candidate_id='{self.candidate_id}', name='{self.name}')>"
