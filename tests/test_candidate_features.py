"""
Integration tests for Candidate Streaks, Verification, and Search/Filters (Issue #58).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from database.models import Candidate, InterviewSession
from orchestrator.candidate_manager import candidate_manager
from orchestrator.main import app
from orchestrator.time_utils import utcnow

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    from database.db import SessionLocal
    from database.models.interview_schedule import InterviewSchedule

    db = SessionLocal()
    try:
        db.query(InterviewSession).delete()
        db.query(InterviewSchedule).delete()
        db.query(Candidate).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(InterviewSession).delete()
        db.query(InterviewSchedule).delete()
        db.query(Candidate).delete()
        db.commit()
    finally:
        db.close()


def test_candidate_registration_sends_verification_email():
    """Verify that candidate creation generates verification token and calls email_service."""
    payload = {
        "name": "Jane Coder",
        "email": "jane.coder@example.com",
        "resume_text": "Experienced Python Engineer",
        "skills": ["Python", "FastAPI"],
        "status": "unverified",
        "role": "Backend Engineer",
    }

    with patch(
        "orchestrator.email_service.email_service.send_verification_email"
    ) as mock_send:
        mock_send.return_value = (True, "Email sent successfully")
        response = client.post("/candidates", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Jane Coder"
    assert data["email"] == "jane.coder@example.com"
    assert data["is_verified"] is False
    assert "verification_token" in data
    assert len(data["verification_token"]) == 6
    assert data["status"] == "unverified"
    assert data["role"] == "Backend Engineer"
    mock_send.assert_called_once_with(
        candidate_name="Jane Coder",
        candidate_email="jane.coder@example.com",
        token=data["verification_token"],
    )


def test_candidate_verification_flow():
    """Verify email verification route sets is_verified=True and status=verified."""
    # Create candidate
    payload = {
        "name": "Verify Tester",
        "email": "verify.tester@example.com",
        "role": "QA Engineer",
    }
    create_res = client.post("/candidates", json=payload)
    assert create_res.status_code == 200
    candidate = create_res.json()
    token = candidate["verification_token"]

    # Verify candidate with correct token
    verify_payload = {
        "email": "verify.tester@example.com",
        "token": token,
    }
    verify_res = client.post("/candidates/verify", json=verify_payload)
    assert verify_res.status_code == 200
    assert verify_res.json()["message"] == "Candidate verified successfully"

    # Fetch candidate to ensure they are verified
    get_res = client.get(f"/candidates/{candidate['candidate_id']}")
    assert get_res.status_code == 200
    updated_cand = get_res.json()
    assert updated_cand["is_verified"] is True
    assert updated_cand["status"] == "verified"

    # Try verifying with incorrect token should fail
    fail_payload = {
        "email": "verify.tester@example.com",
        "token": "000000",
    }
    fail_res = client.post("/candidates/verify", json=fail_payload)
    assert fail_res.status_code == 400


def test_unverified_candidate_cannot_book_schedule():
    """Verify that unverified candidates are blocked from scheduling interviews."""
    # Create unverified candidate
    payload = {
        "name": "Unverified Tester",
        "email": "unverified@example.com",
    }
    create_res = client.post("/candidates", json=payload)
    assert create_res.status_code == 200
    candidate_id = create_res.json()["candidate_id"]

    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    sched_payload = {
        "candidate_id": candidate_id,
        "interviewer_id": "Lead Tester",
        "scheduled_at": tomorrow,
        "notes": "Blocked scheduling test",
        "send_email": False,
    }

    # Attempt to book schedule
    sched_res = client.post("/api/schedule", json=sched_payload)
    assert sched_res.status_code == 400
    assert "must be verified" in sched_res.json()["detail"]

    # Verify the candidate
    verify_res = client.post(
        "/candidates/verify",
        json={
            "email": "unverified@example.com",
            "token": create_res.json()["verification_token"],
        },
    )
    assert verify_res.status_code == 200

    # Attempt booking schedule again - should succeed
    sched_res2 = client.post("/api/schedule", json=sched_payload)
    assert sched_res2.status_code == 201


def test_candidate_search_and_filters():
    """Verify that candidates endpoint supports search, status, and role filter."""
    # Register 3 distinct candidates
    c1 = client.post(
        "/candidates",
        json={
            "name": "Alice Software",
            "email": "alice@corp.com",
            "role": "SWE",
            "status": "unverified",
        },
    ).json()
    c2 = client.post(
        "/candidates",
        json={
            "name": "Bob Frontend",
            "email": "bob@corp.com",
            "role": "Frontend Engineer",
            "status": "verified",
        },
    ).json()
    c3 = client.post(
        "/candidates",
        json={
            "name": "Charlie Manager",
            "email": "charlie@corp.com",
            "role": "Product Manager",
            "status": "verified",
        },
    ).json()

    # Test search by name (substring, case-insensitive)
    res_search = client.get("/candidates?search=alice")
    assert res_search.status_code == 200
    candidates = res_search.json()["candidates"]
    assert any(c["candidate_id"] == c1["candidate_id"] for c in candidates)
    assert not any(c["candidate_id"] == c2["candidate_id"] for c in candidates)

    # Test filter by status
    res_status = client.get("/candidates?status=verified")
    assert res_status.status_code == 200
    candidates_status = res_status.json()["candidates"]
    assert any(c["candidate_id"] == c2["candidate_id"] for c in candidates_status)
    assert any(c["candidate_id"] == c3["candidate_id"] for c in candidates_status)
    assert not any(c["candidate_id"] == c1["candidate_id"] for c in candidates_status)

    # Test filter by role
    res_role = client.get("/candidates?role=frontend%20engineer")
    assert res_role.status_code == 200
    candidates_role = res_role.json()["candidates"]
    assert any(c["candidate_id"] == c2["candidate_id"] for c in candidates_role)
    assert not any(c["candidate_id"] == c3["candidate_id"] for c in candidates_role)

    # Test combinable filters
    res_combined = client.get(
        "/candidates?search=bob&status=verified&role=frontend%20engineer"
    )
    assert res_combined.status_code == 200
    candidates_combined = res_combined.json()["candidates"]
    assert len(candidates_combined) == 1
    assert candidates_combined[0]["candidate_id"] == c2["candidate_id"]


def test_streak_and_badge_logic():
    """Verify that practice streaks are tracked and badges are awarded correctly."""
    # Create and verify candidate
    payload = {
        "name": "Streak Runner",
        "email": "streak.runner@example.com",
    }
    candidate = client.post("/candidates", json=payload).json()
    candidate_id = candidate["candidate_id"]

    # Verify candidate first so we can use sessions/schedules if needed
    client.post(
        "/candidates/verify",
        json={
            "email": "streak.runner@example.com",
            "token": candidate["verification_token"],
        },
    )

    # Day 1: Record practice
    candidate_manager.record_practice(candidate_id)
    cand_d1 = candidate_manager.get_candidate(candidate_id)
    assert cand_d1["practice_streak"] == 1
    assert cand_d1["last_practice_date"] is not None

    # Day 2 consecutive practice simulation
    # Mock utcnow to be tomorrow
    tomorrow = utcnow() + timedelta(days=1)
    with patch("orchestrator.candidate_manager.utcnow", return_value=tomorrow):
        candidate_manager.record_practice(candidate_id)

    cand_d2 = candidate_manager.get_candidate(candidate_id)
    assert cand_d2["practice_streak"] == 2

    # Day 3 consecutive practice simulation
    day3 = tomorrow + timedelta(days=1)
    with patch("orchestrator.candidate_manager.utcnow", return_value=day3):
        candidate_manager.record_practice(candidate_id)

    cand_d3 = candidate_manager.get_candidate(candidate_id)
    assert cand_d3["practice_streak"] == 3
    assert "3-Day Streak" in cand_d3["badges"]

    # Streak broken simulation (skip a day)
    day5 = day3 + timedelta(days=2)  # skip day 4
    with patch("orchestrator.candidate_manager.utcnow", return_value=day5):
        candidate_manager.record_practice(candidate_id)

    cand_d5 = candidate_manager.get_candidate(candidate_id)
    assert cand_d5["practice_streak"] == 1
