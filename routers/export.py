from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from orchestrator.session_manager import SessionManager

router = APIRouter()

session_manager = SessionManager()


def _get_transcript_fields(session_id: str, session_data: dict) -> tuple[list, list]:
    """
    Get questions_asked and answers_provided for a session.

    SessionManager may return these fields from Redis. If they are
    unavailable there, fall back to the corresponding Postgres columns.
    """
    questions = session_data.get("questions_asked")
    answers = session_data.get("answers_provided")

    if questions is None or answers is None:
        db = SessionLocal()
        try:
            interview = db.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()
        finally:
            db.close()

        if interview:
            if questions is None:
                questions = interview.questions_asked
            if answers is None:
                answers = interview.answers_provided

    return questions or [], answers or []


@router.get("/sessions/{session_id}/export/pdf")
def export_interview_transcript(session_id: str):
    """Export the interview Q&A transcript as a downloadable PDF."""
    session_data = session_manager.get_session(session_id)

    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    questions, answers = _get_transcript_fields(session_id, session_data)

    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            "Interview Transcript",
            styles["Title"],
        )
    )
    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            f"Session ID: {escape(session_id)}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 15))

    for index, question in enumerate(questions, start=1):
        story.append(
            Paragraph(
                f"<b>Question {index}</b>",
                styles["Heading3"],
            )
        )

        if isinstance(question, dict):
            question_text = question.get("text") or question.get("question") or ""
        else:
            question_text = str(question)

        story.append(
            Paragraph(
                escape(str(question_text)),
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 8))

        answer_text = ""

        if index - 1 < len(answers):
            answer = answers[index - 1]

            if isinstance(answer, dict):
                answer_text = (
                    answer.get("answer_text")
                    or answer.get("answer")
                    or answer.get("text")
                    or answer.get("response")
                    or ""
                )
            else:
                answer_text = str(answer)

        story.append(
            Paragraph(
                f"<b>Answer:</b> {escape(str(answer_text))}",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 15))

    document.build(story)

    pdf_buffer.seek(0)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="interview_{session_id}.pdf"'
            )
        },
    )
