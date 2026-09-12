"""Integration coverage for retrieved questions reaching a live interview."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base
from database.models import Question
from orchestrator.main import app, question_bank
from orchestrator.question_bank import get_personalized_questions


def test_retrieved_questions_surface_in_live_interview(monkeypatch):
    resume = """
    Maya Chen is a senior machine learning engineer with six years of experience
    building Python services, feature pipelines, and model monitoring for fraud
    detection. She deployed scikit-learn and PyTorch models behind REST APIs and
    used PostgreSQL, Redis, and AWS at scale.
    """
    job_description = """
    We are hiring a Machine Learning Platform Engineer to productionize models.
    The role requires Python, PyTorch, feature engineering, model monitoring,
    REST APIs, PostgreSQL, Redis, and AWS. Candidates should explain design
    decisions and production trade-offs clearly.
    """
    retrieved_documents = [
        "Explain how you would monitor a PyTorch fraud model in production and detect data drift.",
    ]

    monkeypatch.setattr(
        "retrieval.index.index",
        SimpleNamespace(sample_docs=retrieved_documents),
    )

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(bind=test_engine)
    monkeypatch.setattr("orchestrator.question_bank.SessionLocal", test_session)
    monkeypatch.setattr(Question, "tags", None, raising=False)

    try:
        personalized_questions = get_personalized_questions(
            candidate_id="maya-chen",
            resume_text=resume,
            jd_text=job_description,
            count=3,
        )

        assert personalized_questions == retrieved_documents

        with test_session() as db:
            for question_number, text in enumerate(personalized_questions, start=1):
                db.add(
                    Question(
                        question_id=f"rag-q-{question_number}",
                        text=text,
                        category="technical",
                        difficulty="hard",
                        tag="machine-learning-platform",
                        usage_count=0,
                        created_at=datetime(2024, 1, 1)
                        + timedelta(days=3 - question_number),
                        updated_at=datetime(2024, 1, 1),
                    )
                )
            db.commit()

        assert [
            question["text"] for question in question_bank.get_questions(limit=3)
        ] == retrieved_documents

        session_state = {
            "session_id": "session-rag-integration",
            "candidate_id": "maya-chen",
            "status": "QUEUED",
            "questions_asked": [],
        }
        scheduler = __import__("orchestrator.main", fromlist=["scheduler"]).scheduler
        session_manager = __import__(
            "orchestrator.main", fromlist=["session_manager"]
        ).session_manager

        with (
            patch.object(
                session_manager,
                "create_session",
                return_value=session_state["session_id"],
            ),
            patch.object(session_manager, "get_session", return_value=session_state),
            patch.object(session_manager, "update_session_status"),
            patch.object(session_manager, "start_question_timer"),
            patch.object(scheduler, "can_accept_task", return_value=True),
            patch.object(scheduler, "schedule_task"),
            patch.object(scheduler, "get_estimated_wait_time", return_value=0),
            patch("orchestrator.main.http_cache.invalidate"),
            patch("orchestrator.main.candidate_manager.record_practice"),
            patch(
                "workers.ai_client.synthesize_speech", return_value=b"mock_audio_data"
            ),
        ):
            with TestClient(app) as client:
                start_response = client.post(
                    "/start-interview",
                    headers={"X-API-Token": "ci-test-token"},
                    json={
                        "candidate_id": "maya-chen",
                        "candidate_name": "Maya Chen",
                        "priority": "medium",
                    },
                )
                assert start_response.status_code == 200, start_response.text

                asked_questions = []
                for _ in personalized_questions:
                    response = client.post(
                        "/interviews/ask-question",
                        json={"session_id": session_state["session_id"]},
                    )
                    assert response.status_code == 200, response.text
                    asked_questions.append(response.json()["text"])
                    session_state["questions_asked"].append(
                        {"question_id": response.json()["question_id"]}
                    )

        assert asked_questions == retrieved_documents
    finally:
        Base.metadata.drop_all(test_engine)
        test_engine.dispose()
