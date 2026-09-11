"""
Interview Schedule API Router.
Handles schedule creation, calendar listings, upcoming events, and triggering email notifications.
"""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Candidate, InterviewSchedule
from orchestrator.email_service import email_service
from orchestrator.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {"scheduled", "completed", "cancelled", "rescheduled"}

# Common non-IANA timezone abbreviations mapped to a canonical IANA zone.
# Abbreviations are inherently ambiguous (e.g. IST = India/Israel/Ireland,
# CST = US Central/China), so each entry below picks ONE common meaning.
# Prefer full IANA names (e.g. "Asia/Kolkata") wherever possible; this map
# exists only to accept casual input, not as a source of truth.
TIMEZONE_ABBREVIATIONS = {
    "IST": "Asia/Kolkata",  # India Standard Time
    "EST": "America/New_York",  # US Eastern
    "EDT": "America/New_York",
    "CST": "America/Chicago",  # US Central
    "CDT": "America/Chicago",
    "MST": "America/Denver",  # US Mountain
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",  # US Pacific
    "PDT": "America/Los_Angeles",
    "GMT": "Etc/GMT",
    "BST": "Europe/London",  # British Summer Time
    "CET": "Europe/Paris",
    "JST": "Asia/Tokyo",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
    "SGT": "Asia/Singapore",
    "HKT": "Asia/Hong_Kong",
}


def resolve_timezone(tz_name: str) -> ZoneInfo:
    """
    Resolve a timezone string to a ZoneInfo, accepting either a full IANA
    name (e.g. 'Asia/Kolkata') or a common abbreviation (e.g. 'IST').
    Raises ZoneInfoNotFoundError if neither resolves.
    """
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        canonical = TIMEZONE_ABBREVIATIONS.get(tz_name.strip().upper())
        if canonical:
            return ZoneInfo(canonical)
        raise


class CreateScheduleRequest(BaseModel):
    """Payload for creating a new interview schedule."""

    candidate_id: str = Field(..., description="ID of the candidate")
    interviewer_id: str = Field(
        ..., description="Name or ID of the assigned interviewer"
    )
    scheduled_at: datetime = Field(
        ..., description="ISO datetime string for the scheduled interview"
    )
    timezone: str = Field(
        default="UTC",
        description="IANA timezone name the scheduled_at was entered in, e.g. 'Asia/Kolkata'",
    )
    notes: str | None = Field(
        default=None, description="Optional interview notes or description"
    )
    send_email: bool = Field(
        default=True, description="Whether to send confirmation email via smtplib"
    )


class UpdateScheduleRequest(BaseModel):
    """Payload for updating schedule status or details."""

    status: str | None = Field(default=None, description="New schedule status")
    notes: str | None = Field(default=None, description="Updated notes")
    scheduled_at: datetime | None = Field(
        default=None, description="Rescheduled datetime"
    )


def create_schedule_routes() -> APIRouter:
    """Create APIRouter for interview scheduling."""

    router = APIRouter(prefix="/api/schedule", tags=["Schedule"])

    @router.post("", status_code=201)
    async def create_schedule(
        payload: CreateScheduleRequest,
        db: Session = Depends(get_db),
    ):
        """
        Create a new interview schedule and trigger an email notification to the candidate.
        Validates future date/time. Candidate existence is NOT enforced — any
        candidate_id string is accepted; if it doesn't match a real Candidate
        record, name/email fall back to the raw ID / None.
        """
        try:
            # Look up candidate if it exists, but don't require it.
            candidate = db.execute(
                select(Candidate).where(Candidate.candidate_id == payload.candidate_id)
            ).scalar_one_or_none()

            candidate_name = candidate.name if candidate else payload.candidate_id
            candidate_email = candidate.email if candidate else None

            # Ensure datetime is timezone-aware.
            # Localize using the booking timezone, then convert to UTC for storage.
            # This fixes midnight-boundary bugs: e.g. 2026-08-20T23:30 in
            # Asia/Kolkata is 2026-08-20T18:00 UTC, not the next calendar day.
            try:
                booking_tz = resolve_timezone(payload.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown timezone: '{payload.timezone}'",
                )

            scheduled_at = payload.scheduled_at
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=booking_tz)
            else:
                scheduled_at = scheduled_at.astimezone(booking_tz)

            scheduled_at = scheduled_at.astimezone(timezone.utc)

            # Validate that scheduled_at is in the future
            now_utc = datetime.now(timezone.utc)
            if scheduled_at <= now_utc:
                raise HTTPException(
                    status_code=400,
                    detail="Scheduled date and time must be in the future.",
                )

            # Create Schedule ORM entry
            schedule = InterviewSchedule(
                candidate_id=payload.candidate_id,
                interviewer_id=payload.interviewer_id,
                scheduled_at=scheduled_at,
                timezone=booking_tz.key,  # canonical IANA name, not the raw
                # input (e.g. "IST" -> "Asia/Kolkata"),
                # so downstream Intl.DateTimeFormat
                # calls on the frontend always get a
                # valid IANA zone name.
                status="scheduled",
                notes=payload.notes,
            )

            db.add(schedule)
            db.commit()
            db.refresh(schedule)

            # Send Email Notification
            email_sent = False
            email_msg = "Email notification disabled."

            if payload.send_email and candidate_email:
                date_str = scheduled_at.strftime("%B %d, %Y")
                time_str = scheduled_at.strftime("%I:%M %p %Z").strip()

                email_sent, email_msg = email_service.send_interview_confirmation(
                    candidate_name=candidate_name,
                    candidate_email=candidate_email,
                    interview_date=date_str,
                    interview_time=time_str,
                    interviewer_name=payload.interviewer_id,
                    schedule_id=schedule.id,
                    notes=payload.notes,
                )
            elif payload.send_email and not candidate_email:
                email_msg = "Email notification skipped: no email on file for this candidate_id."

            return {
                "message": "Interview scheduled successfully.",
                "schedule": {
                    "id": schedule.id,
                    "candidate_id": schedule.candidate_id,
                    "candidate_name": candidate_name,
                    "candidate_email": candidate_email,
                    "interviewer_id": schedule.interviewer_id,
                    "scheduled_at": schedule.scheduled_at.isoformat(),
                    "timezone": schedule.timezone,
                    "status": schedule.status,
                    "notes": schedule.notes,
                    "created_at": schedule.created_at.isoformat(),
                },
                "email_notification": {
                    "sent": email_sent,
                    "detail": email_msg,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error scheduling interview: {e!s}")
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to schedule interview: {e!s}"
            )

    @router.get("")
    async def list_schedules(
        candidate_id: str | None = Query(default=None),
        status: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        db: Session = Depends(get_db),
    ):
        """List all interview schedules with candidate details."""
        try:
            stmt = select(InterviewSchedule, Candidate).join(
                Candidate,
                InterviewSchedule.candidate_id == Candidate.candidate_id,
                isouter=True,
            )

            if candidate_id:
                stmt = stmt.where(InterviewSchedule.candidate_id == candidate_id)

            if status:
                clean_status = status.strip().lower()
                stmt = stmt.where(InterviewSchedule.status == clean_status)

            stmt = stmt.order_by(InterviewSchedule.scheduled_at.asc()).limit(limit)
            results = db.execute(stmt).all()

            schedules_data = []

            for sched, cand in results:
                schedules_data.append(
                    {
                        "id": sched.id,
                        "candidate_id": sched.candidate_id,
                        "candidate_name": cand.name if cand else sched.candidate_id,
                        "candidate_email": cand.email if cand else None,
                        "interviewer_id": sched.interviewer_id,
                        "scheduled_at": sched.scheduled_at.isoformat(),
                        "timezone": sched.timezone,
                        "status": sched.status,
                        "notes": sched.notes,
                        "created_at": sched.created_at.isoformat(),
                    }
                )

            return {
                "count": len(schedules_data),
                "schedules": schedules_data,
            }

        except Exception as e:
            logger.error(f"Error fetching schedules: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching interview schedules",
            )

    @router.get("/upcoming")
    async def list_upcoming_schedules(
        limit: int = Query(default=10, ge=1, le=50),
        db: Session = Depends(get_db),
    ):
        """List upcoming scheduled interviews from the current time onwards."""
        try:
            now = datetime.now(timezone.utc)

            stmt = (
                select(InterviewSchedule, Candidate)
                .join(
                    Candidate,
                    InterviewSchedule.candidate_id == Candidate.candidate_id,
                    isouter=True,
                )
                .where(InterviewSchedule.scheduled_at >= now)
                .where(InterviewSchedule.status == "scheduled")
                .order_by(InterviewSchedule.scheduled_at.asc())
                .limit(limit)
            )

            results = db.execute(stmt).all()

            upcoming_data = []

            for sched, cand in results:
                upcoming_data.append(
                    {
                        "id": sched.id,
                        "candidate_id": sched.candidate_id,
                        "candidate_name": cand.name if cand else sched.candidate_id,
                        "candidate_email": cand.email if cand else None,
                        "interviewer_id": sched.interviewer_id,
                        "scheduled_at": sched.scheduled_at.isoformat(),
                        "timezone": sched.timezone,
                        "status": sched.status,
                        "notes": sched.notes,
                    }
                )

            return {
                "count": len(upcoming_data),
                "upcoming": upcoming_data,
            }

        except Exception as e:
            logger.error(f"Error fetching upcoming schedules: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching upcoming schedules",
            )

    @router.get("/{schedule_id}")
    async def get_schedule(
        schedule_id: str,
        db: Session = Depends(get_db),
    ):
        """Get details for a specific interview schedule."""
        try:
            stmt = (
                select(InterviewSchedule, Candidate)
                .join(
                    Candidate,
                    InterviewSchedule.candidate_id == Candidate.candidate_id,
                    isouter=True,
                )
                .where(InterviewSchedule.id == schedule_id)
            )

            result = db.execute(stmt).first()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Schedule not found",
                )

            sched, cand = result

            return {
                "id": sched.id,
                "candidate_id": sched.candidate_id,
                "candidate_name": cand.name if cand else sched.candidate_id,
                "candidate_email": cand.email if cand else None,
                "interviewer_id": sched.interviewer_id,
                "scheduled_at": sched.scheduled_at.isoformat(),
                "timezone": sched.timezone,
                "status": sched.status,
                "notes": sched.notes,
                "created_at": sched.created_at.isoformat(),
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error getting schedule: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error getting schedule details",
            )

    @router.patch("/{schedule_id}")
    async def update_schedule(
        schedule_id: str,
        payload: UpdateScheduleRequest,
        db: Session = Depends(get_db),
    ):
        """
        Update interview schedule status or datetime with strict validation.

        When the status actually changes to 'cancelled' or 'rescheduled',
        exactly one corresponding notification is created.
        """
        try:
            schedule = db.execute(
                select(InterviewSchedule).where(InterviewSchedule.id == schedule_id)
            ).scalar_one_or_none()

            if not schedule:
                raise HTTPException(
                    status_code=404,
                    detail="Schedule not found",
                )

            # Store the original status before making any changes.
            # This is required to detect a real status transition and prevent
            # duplicate notifications when the same status is submitted again.
            old_status = schedule.status

            new_status = None

            # Validate status input
            if payload.status is not None:
                clean_status = payload.status.strip().lower()

                if clean_status not in ALLOWED_STATUSES:
                    allowed_str = ", ".join(sorted(ALLOWED_STATUSES))

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid status '{payload.status}'. "
                            f"Allowed statuses are: {allowed_str}"
                        ),
                    )

                new_status = clean_status
                schedule.status = clean_status

            if payload.notes is not None:
                schedule.notes = payload.notes

            # Validate future datetime
            if payload.scheduled_at is not None:
                sched_at = payload.scheduled_at

                if sched_at.tzinfo is None:
                    sched_at = sched_at.replace(tzinfo=timezone.utc)

                now_utc = datetime.now(timezone.utc)

                if sched_at <= now_utc:
                    raise HTTPException(
                        status_code=400,
                        detail="Scheduled date and time must be in the future.",
                    )

                schedule.scheduled_at = sched_at

            # Save the schedule changes first.
            db.commit()
            db.refresh(schedule)

            # Trigger notification only for an actual transition to
            # 'cancelled' or 'rescheduled'.
            #
            # Examples:
            # scheduled -> cancelled     = notification
            # scheduled -> rescheduled   = notification
            # cancelled -> cancelled     = no notification
            # rescheduled -> rescheduled = no notification
            # scheduled -> completed     = no notification
            if (
                new_status is not None
                and old_status != new_status
                and new_status in {"cancelled", "rescheduled"}
            ):
                notification_manager = NotificationManager(db=db)

                notification_manager.notify_schedule_status_change(
                    user_id=schedule.candidate_id,
                    new_status=new_status,
                )

            return {
                "message": "Schedule updated successfully",
                "schedule": {
                    "id": schedule.id,
                    "status": schedule.status,
                    "scheduled_at": schedule.scheduled_at.isoformat(),
                    "timezone": schedule.timezone,
                    "notes": schedule.notes,
                },
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error updating schedule: {e!s}")
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Error updating schedule",
            )

    return router
