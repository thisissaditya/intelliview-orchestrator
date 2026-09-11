"""
Unit tests for the new dashboard summary endpoint on dashboard_api.py
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database.db import Base, SessionLocal, engine
from database.models import Candidate, InterviewSchedule, InterviewSession
from monitoring.dashboard_api import create_dashboard_routes
from orchestrator import http_cache


@pytest.fixture(autouse=True)
def _clear_summary_cache():
    """The /metrics/summary route is cached in Redis under a fixed key
    (see orchestrator/http_cache.py), independent of which app/dependencies
    produced the response. Without clearing it, a cache hit from an earlier
    test can leak into a later test within the same TTL window and make
    assertions fail against stale data. Invalidate before and after each
    test so every test observes a fresh computation.
    """
    http_cache.invalidate("monitoring.metrics.summary")
    yield
    http_cache.invalidate("monitoring.metrics.summary")


@pytest.fixture
def mock_dependencies():
    return {
        "metrics_collector": MagicMock(),
        "session_manager": MagicMock(),
        "worker_registry": MagicMock(),
        "session_tracker": MagicMock(),
        "fault_manager": MagicMock(),
        "retry_manager": MagicMock(),
        "health_monitor": MagicMock(),
        "ws_manager": MagicMock(),
    }


@pytest.fixture
def client_with_routes(mock_dependencies):
    app = FastAPI()
    router = create_dashboard_routes(**mock_dependencies)
    app.include_router(router, prefix="/monitoring")
    return TestClient(app)


def test_summary_endpoint_with_mocked_dependencies(
    client_with_routes, mock_dependencies
):
    mock_dependencies["session_tracker"].get_session_statistics.return_value = {
        "active_sessions": 5
    }
    mock_dependencies["worker_registry"].get_worker_statistics.return_value = {
        "healthy_workers": 3
    }

    response = client_with_routes.get("/monitoring/metrics/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["metrics"]["active_sessions"] == 5
    assert data["metrics"]["healthy_workers"] == 3
    assert "todays_interviews" in data["metrics"]
    assert "timestamp" in data


def test_summary_endpoint_fallback_to_metrics_collector(mock_dependencies):
    mock_dependencies["session_tracker"] = None
    mock_dependencies["worker_registry"] = None
    mock_dependencies["metrics_collector"].get_system_metrics.return_value = {
        "session_metrics": {"active": 7},
        "worker_metrics": {"healthy_workers": 4},
    }

    app = FastAPI()
    router = create_dashboard_routes(**mock_dependencies)
    app.include_router(router, prefix="/monitoring")
    client = TestClient(app)

    response = client.get("/monitoring/metrics/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["metrics"]["active_sessions"] == 7
    assert data["metrics"]["healthy_workers"] == 4


def test_summary_endpoint_db_integration():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cand_id = f"cand_test_summary_{int(now.timestamp())}"
        cand = Candidate(
            candidate_id=cand_id,
            name="Test Candidate",
            email=f"candapi_{int(now.timestamp())}@example.com",
        )
        db.add(cand)
        db.flush()

        sess_id = f"sess_test_summary_{int(now.timestamp())}"
        sess = InterviewSession(
            session_id=sess_id,
            candidate_id=cand_id,
            status="PROCESSING",
            created_at=now,
            start_time=now,
        )
        db.add(sess)

        sched_id = f"sched_test_summary_{int(now.timestamp())}"
        sched = InterviewSchedule(
            id=sched_id,
            candidate_id=cand_id,
            interviewer_id="interviewer_1",
            scheduled_at=now + timedelta(hours=1),
            status="scheduled",
        )
        db.add(sched)
        db.commit()

        from monitoring.metrics_collector import MetricsCollector
        from orchestrator.session_tracker import SessionTracker
        from orchestrator.worker_registry import WorkerRegistry

        tracker = SessionTracker()
        registry = WorkerRegistry()
        collector = MetricsCollector()

        registry.register_worker("worker_test_1", capacity=4)

        app = FastAPI()
        router = create_dashboard_routes(
            metrics_collector=collector,
            session_manager=MagicMock(),
            worker_registry=registry,
            session_tracker=tracker,
            fault_manager=MagicMock(),
            retry_manager=MagicMock(),
            health_monitor=MagicMock(),
            ws_manager=MagicMock(),
        )
        app.include_router(router, prefix="/monitoring")
        client = TestClient(app)

        response = client.get("/monitoring/metrics/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["metrics"]["active_sessions"] >= 1
        assert data["metrics"]["healthy_workers"] >= 1
        # Only the InterviewSession row counts toward today's interviews.
        # The InterviewSchedule row created above must not add to this count,
        # since it represents the same interview, not a second one.
        assert data["metrics"]["todays_interviews"] == 1

    finally:
        db.rollback()

        if "sess_id" in locals():
            db.query(InterviewSession).filter(
                InterviewSession.session_id == sess_id
            ).delete()

        if "sched_id" in locals():
            db.query(InterviewSchedule).filter(
                InterviewSchedule.id == sched_id
            ).delete()

        if "cand_id" in locals():
            db.query(Candidate).filter(Candidate.candidate_id == cand_id).delete()

        db.commit()
        db.close()
