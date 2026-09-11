import pytest
from fastapi import HTTPException

from orchestrator.auth import (
    create_access_token,
    require_token,
    verify_access_token,
)


def test_require_token_accepts_valid_token(monkeypatch):
    monkeypatch.setattr("orchestrator.auth.API_TOKEN", "test-secure-token")

    require_token("test-secure-token")


def test_require_token_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr("orchestrator.auth.API_TOKEN", "test-secure-token")

    with pytest.raises(HTTPException) as exc:
        require_token("wrong-token")

    assert exc.value.status_code == 401


def test_require_token_rejects_missing_token(monkeypatch):
    monkeypatch.setattr("orchestrator.auth.API_TOKEN", "test-secure-token")

    with pytest.raises(HTTPException) as exc:
        require_token(None)

    assert exc.value.status_code == 401


def test_require_token_rejects_default_token(monkeypatch):
    monkeypatch.setattr("orchestrator.auth.API_TOKEN", "dev-token-change-me")

    with pytest.raises(HTTPException) as exc:
        require_token("dev-token-change-me")

    assert exc.value.status_code == 500


def test_require_token_rejects_missing_configuration(monkeypatch):
    monkeypatch.setattr("orchestrator.auth.API_TOKEN", "")

    with pytest.raises(HTTPException) as exc:
        require_token("anything")

    assert exc.value.status_code == 500


def test_create_and_verify_access_token(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.auth.JWT_SECRET_KEY",
        "test-jwt-secret",
    )

    token = create_access_token({"sub": "test-user"})
    payload = verify_access_token(token)

    assert payload is not None
    assert payload["sub"] == "test-user"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_access_token_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.auth.JWT_SECRET_KEY",
        "test-jwt-secret",
    )

    payload = verify_access_token("invalid.jwt.token")

    assert payload is None
