from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.practice_sessions import router


class FakeCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, **kwargs):
        self.data[key] = value


def test_practice_session_allows_multiple_attempts(monkeypatch):
    fake_cache = FakeCache()

    monkeypatch.setattr(
        "routers.practice_sessions._get_cache",
        lambda: fake_cache,
    )

    app = FastAPI()

    # Bypass authentication for this isolated router test.
    from routers import practice_sessions

    app.dependency_overrides[practice_sessions.get_current_user] = lambda: {
        "user_id": "test-user"
    }

    app.include_router(router)

    client = TestClient(app)

    response = client.post(
        "/practice-sessions",
        json={
            "candidate_id": "candidate_test",
            "question_id": "question_1",
        },
    )

    assert response.status_code == 200

    practice_session_id = response.json()["practice_session_id"]

    for number in range(1, 6):
        response = client.post(
            f"/practice-sessions/{practice_session_id}/attempts",
            json={"answer": f"practice answer {number}"},
        )

        assert response.status_code == 200
        assert response.json()["practice_session"]["attempt_count"] == number


def test_practice_attempts_do_not_use_retry_manager(monkeypatch):
    fake_cache = FakeCache()

    monkeypatch.setattr(
        "routers.practice_sessions._get_cache",
        lambda: fake_cache,
    )

    app = FastAPI()

    from routers import practice_sessions

    app.dependency_overrides[practice_sessions.get_current_user] = lambda: {
        "user_id": "test-user"
    }

    app.include_router(router)

    client = TestClient(app)

    response = client.post(
        "/practice-sessions",
        json={
            "candidate_id": "candidate_test",
            "question_id": "question_1",
        },
    )

    assert response.status_code == 200

    session_id = response.json()["practice_session_id"]

    response = client.post(
        f"/practice-sessions/{session_id}/attempts",
        json={"answer": "test answer"},
    )

    assert response.status_code == 200

    # Practice data uses separate Redis keys.
    assert any(key.startswith("practice_session:") for key in fake_cache.data)

    assert any(key.startswith("practice_attempts:") for key in fake_cache.data)

    # Real retry_count key must never be created.
    assert not any(key.startswith("retry_count:") for key in fake_cache.data)
