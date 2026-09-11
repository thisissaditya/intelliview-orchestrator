"""Unit tests for the Redis-backed rate limiter middleware."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orchestrator.rate_limiter import RateLimiterMiddleware


@pytest.fixture
def mock_redis():
    """Provide a mocked Redis client with a pipeline."""
    redis_client = MagicMock()
    pipeline = MagicMock()
    redis_client.raw.pipeline.return_value = pipeline
    return redis_client, pipeline


@pytest.fixture
def app(mock_redis):
    """Create a minimal FastAPI app with the rate limiter."""
    redis_client, pipeline = mock_redis

    app = FastAPI()
    app.add_middleware(
        RateLimiterMiddleware,
        limit=2,
        window_seconds=60,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/protected")
    async def protected():
        return {"status": "ok"}

    with patch(
        "orchestrator.rate_limiter.CacheManager",
        return_value=redis_client,
    ):
        yield app, pipeline


def test_requests_within_limit_are_allowed(app):
    """Requests at or below the configured limit should succeed."""
    application, pipeline = app
    pipeline.execute.return_value = [0, 1, 1, True]

    with TestClient(application) as client:
        response = client.get("/protected")

    assert response.status_code == 200
    pipeline.execute.assert_called_once()


def test_request_over_limit_returns_429(app):
    """Requests above the configured limit should return HTTP 429."""
    application, pipeline = app
    pipeline.execute.return_value = [0, 1, 3, True]

    with TestClient(application) as client:
        response = client.get("/protected")

    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"
    assert "retry_after" in response.json()
    assert "Retry-After" in response.headers


def test_exempt_health_path_bypasses_rate_limiter(app):
    """Health checks should not consume rate-limit capacity."""
    application, pipeline = app

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    pipeline.execute.assert_not_called()


def test_client_key_uses_ip_and_api_token(app):
    """Rate-limit identity should include client IP and optional API token."""
    _application, _ = app

    request = MagicMock()
    request.headers.get.side_effect = lambda name, default="": {
        "x-forwarded-for": "192.0.2.10",
        "x-api-token": "test-token",
    }.get(name, default)
    request.client.host = "127.0.0.1"

    key = RateLimiterMiddleware._client_key(request)

    assert key == "192.0.2.10:test-token"


@pytest.mark.parametrize(
    "path",
    ["/health", "/docs", "/openapi.json"],
)
def test_documented_exempt_paths_bypass_rate_limiter(app, path):
    """All documented exempt paths should bypass rate limiting."""
    application, pipeline = app

    with TestClient(application) as client:
        response = client.get(path)

    assert response.status_code == 200
    pipeline.execute.assert_not_called()
