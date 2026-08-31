"""
Candidate Manager
Manages candidate profiles, interview history, and scoring
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Text, cast, or_, select

from database.db import SessionLocal
from database.models import Candidate, InterviewSession
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class CandidateManager:
    """Manages candidate profiles, history, and scoring."""

    def __init__(self):
        pass

    def create_candidate(
        self,
        name: str,
        email: str,
        resume_text: str | None = None,
        skills: list[str] | None = None,
        status: str | None = "unverified",
        role: str | None = None,
    ) -> dict[str, Any]:
        """Create a new candidate profile"""
        import random

        candidate_id = f"candidate_{uuid.uuid4().hex[:12]}"
        now = utcnow()
        token = "".join(random.choices("0123456789", k=6))
        db = SessionLocal()

        try:
            candidate = Candidate(
                candidate_id=candidate_id,
                name=name.strip(),
                email=email.strip().lower(),
                resume_text=resume_text,
                skills=skills or [],
                interview_history=[],
                avg_score=None,
                total_interviews=0,
                is_verified=False,
                verification_token=token,
                practice_streak=0,
                last_practice_date=None,
                badges=[],
                status=status or "unverified",
                role=role,
                created_at=now,
                updated_at=now,
            )

            db.add(candidate)
            db.commit()

            return {
                "candidate_id": candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "resume_text": resume_text,
                "skills": skills or [],
                "interview_history": [],
                "avg_score": None,
                "total_interviews": 0,
                "is_verified": False,
                "verification_token": token,
                "practice_streak": 0,
                "last_practice_date": None,
                "badges": [],
                "status": status or "unverified",
                "role": role,
                "created_at": now.isoformat(),
            }

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:

        db = SessionLocal()

        try:
            c = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if not c:
                return None

            return {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "email": c.email,
                "resume_text": c.resume_text,
                "skills": c.skills or [],
                "interview_history": c.interview_history or [],
                "avg_score": c.avg_score,
                "total_interviews": c.total_interviews,
                "is_verified": getattr(c, "is_verified", False),
                "verification_token": getattr(c, "verification_token", None),
                "practice_streak": getattr(c, "practice_streak", 0),
                "last_practice_date": (
                    c.last_practice_date.isoformat()
                    if getattr(c, "last_practice_date", None)
                    else None
                ),
                "badges": getattr(c, "badges", []) or [],
                "status": getattr(c, "status", "unverified"),
                "role": getattr(c, "role", None),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }

        finally:
            db.close()

    def update_candidate(
        self,
        candidate_id: str,
        name: str,
        email: str,
        resume_text: str | None = None,
        skills: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update editable candidate profile fields."""

        db = SessionLocal()

        try:
            candidate = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if not candidate:
                return None

            candidate.name = name.strip()
            candidate.email = email.strip().lower()
            candidate.resume_text = resume_text
            candidate.skills = skills or []
            candidate.updated_at = utcnow()

            db.commit()
            db.refresh(candidate)

            return {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "resume_text": candidate.resume_text,
                "skills": candidate.skills or [],
                "interview_history": candidate.interview_history or [],
                "avg_score": candidate.avg_score,
                "total_interviews": candidate.total_interviews,
                "created_at": (
                    candidate.created_at.isoformat() if candidate.created_at else None
                ),
                "updated_at": (
                    candidate.updated_at.isoformat() if candidate.updated_at else None
                ),
            }

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def list_candidates(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        role: str | None = None,
        skill: str | None = None,
        position: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import func

        db = SessionLocal()

        try:
            query = select(Candidate)

            if search and search.strip():
                value = search.strip()

                query = query.where(
                    or_(
                        Candidate.name.ilike(f"%{value}%"),
                        Candidate.email.ilike(f"%{value}%"),
                    )
                )

            if status and status.strip():
                query = query.where(
                    func.lower(Candidate.status) == status.strip().lower()
                )

            if role and role.strip():
                query = query.where(func.lower(Candidate.role) == role.strip().lower())

            if skill and skill.strip():

                query = query.where(
                    cast(Candidate.skills, Text).ilike(f"%{skill.strip()}%")
                )

            # Position filter
            if position and position.strip():
                query = query.where(
                    Candidate.interview_sessions.any(
                        InterviewSession.position.ilike(f"%{position.strip()}%")
                    )
                )

            # Date range filter
            if date_from:
                start_date = datetime.fromisoformat(date_from)
                query = query.where(Candidate.created_at >= start_date)

            if date_to:
                end_date = datetime.fromisoformat(date_to) + timedelta(days=1)
                query = query.where(Candidate.created_at < end_date)

            rows = (
                db.execute(
                    query.order_by(Candidate.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            return [
                {
                    "candidate_id": c.candidate_id,
                    "name": c.name,
                    "email": c.email,
                    "skills": c.skills or [],
                    "avg_score": c.avg_score,
                    "total_interviews": c.total_interviews,
                    "is_verified": getattr(c, "is_verified", False),
                    "verification_token": getattr(c, "verification_token", None),
                    "practice_streak": getattr(c, "practice_streak", 0),
                    "last_practice_date": (
                        c.last_practice_date.isoformat()
                        if getattr(c, "last_practice_date", None)
                        else None
                    ),
                    "badges": getattr(c, "badges", []) or [],
                    "status": getattr(c, "status", "unverified"),
                    "role": getattr(c, "role", None),
                    "active_sessions": sum(
                        1
                        for session in c.interview_sessions
                        if session.status
                        not in {"COMPLETED", "FAILED", "TIMEOUT", "CANCELLED"}
                    ),
                    "completed_sessions": sum(
                        1
                        for session in c.interview_sessions
                        if session.status == "COMPLETED"
                    ),
                    "created_at": (c.created_at.isoformat() if c.created_at else None),
                    "updated_at": (c.updated_at.isoformat() if c.updated_at else None),
                }
                for c in rows
            ]

        except Exception as e:
            logger.error(f"Error listing candidates: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error listing candidates",
            )

        finally:
            db.close()

    def delete_candidate(self, candidate_id: str) -> bool:

        db = SessionLocal()

        try:

            c = db.execute(
                select(Candidate).where(
                    Candidate.candidate_id == candidate_id,
                    Candidate.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            if not c:
                return False

            c.deleted_at = utcnow()
            db.commit()
            return True

        finally:
            db.close()

    def verify_candidate(self, email: str, token: str) -> bool:
        """Verify candidate's email by checking token"""
        db = SessionLocal()
        try:
            c = db.execute(
                select(Candidate).where(Candidate.email == email.strip().lower())
            ).scalar_one_or_none()
            if not c or c.verification_token != token.strip():
                return False
            c.is_verified = True
            c.status = "verified"
            c.verification_token = None
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error verifying candidate {email}: {e}")
            return False
        finally:
            db.close()

    def record_practice(self, candidate_id: str) -> None:
        """Update consecutive practice day streak and badges for a candidate."""
        from datetime import timedelta, timezone

        from sqlalchemy import func

        db = SessionLocal()
        try:
            candidate = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()
            if not candidate:
                return

            now_utc = utcnow()
            today_date = now_utc.date()

            last_practice = candidate.last_practice_date
            if last_practice:
                if last_practice.tzinfo is None:
                    last_practice = last_practice.replace(tzinfo=timezone.utc)
                last_date = last_practice.astimezone(timezone.utc).date()
            else:
                last_date = None

            streak = candidate.practice_streak or 0
            if last_date is None:
                streak = 1
            elif last_date == today_date:
                pass
            elif last_date == today_date - timedelta(days=1):
                streak += 1
            else:
                streak = 1

            candidate.practice_streak = streak
            candidate.last_practice_date = now_utc

            badges = list(candidate.badges or [])
            if streak >= 30 and "30-Day Streak" not in badges:
                badges.append("30-Day Streak")
            elif streak >= 14 and "14-Day Streak" not in badges:
                badges.append("14-Day Streak")
            elif streak >= 7 and "7-Day Streak" not in badges:
                badges.append("7-Day Streak")
            elif streak >= 3 and "3-Day Streak" not in badges:
                badges.append("3-Day Streak")

            total_sessions = (
                db.execute(
                    select(func.count(InterviewSession.session_id)).where(
                        InterviewSession.candidate_id == candidate_id
                    )
                ).scalar()
                or 0
            )

            if total_sessions >= 10 and "Interview Veteran" not in badges:
                badges.append("Interview Veteran")
            elif total_sessions >= 5 and "Interview Enthusiast" not in badges:
                badges.append("Interview Enthusiast")
            elif total_sessions >= 1 and "First Interview" not in badges:
                badges.append("First Interview")

            candidate.badges = badges
            db.commit()
            logger.info(
                f"Recorded practice for candidate {candidate_id}. Streak: {streak}, Badges: {badges}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording practice for candidate {candidate_id}: {e}")
        finally:
            db.close()

    def update_candidate_score(
        self,
        candidate_id: str,
        session_id: str,
        score: float,
    ) -> bool:

        db = SessionLocal()

        try:
            c = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if not c:
                return False

            history = list(c.interview_history or [])

            history.append(
                {
                    "session_id": session_id,
                    "score": score,
                    "completed_at": utcnow().isoformat(),
                }
            )

            total = c.total_interviews + 1

            if c.avg_score is None:
                c.avg_score = score
            else:
                c.avg_score = ((c.avg_score * c.total_interviews) + score) / total

            c.interview_history = history
            c.total_interviews = total
            c.updated_at = utcnow()

            db.commit()
            db.close()

            # Record practice outside active session transaction to avoid locking
            self.record_practice(candidate_id)
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating candidate score: {e}")
            return False

        finally:
            try:
                db.close()
            except Exception:
                pass

    def get_interview_history(
        self,
        candidate_id: str,
    ) -> list[dict[str, Any]]:

        db = SessionLocal()

        try:
            rows = (
                db.execute(
                    select(InterviewSession)
                    .where(InterviewSession.candidate_id == candidate_id)
                    .order_by(InterviewSession.created_at.desc())
                )
                .scalars()
                .all()
            )

            return [
                {
                    "session_id": r.session_id,
                    "status": r.status,
                    "overall_score": r.overall_score,
                    "risk_score": r.risk_score,
                    "start_time": (r.start_time.isoformat() if r.start_time else None),
                    "end_time": (r.end_time.isoformat() if r.end_time else None),
                    "created_at": (r.created_at.isoformat() if r.created_at else None),
                }
                for r in rows
            ]

        finally:
            db.close()


candidate_manager = CandidateManager()
