import logging

import workers.ai_client as ai_client


def test_retry_with_backoff_retries_transient_failure(monkeypatch, caplog):
    attempts = {"count": 0}

    def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary audio failure")
        return {"text": "success"}

    monkeypatch.setattr(ai_client.time, "sleep", lambda _: None)

    with caplog.at_level(logging.WARNING):
        result = ai_client._retry_with_backoff(
            flaky_operation,
            "Test audio operation",
        )

    assert result == {"text": "success"}
    assert attempts["count"] == 3
    assert "retrying" in caplog.text


def test_retry_with_backoff_returns_none_after_max_retries(monkeypatch, caplog):
    attempts = {"count": 0}

    def failing_operation():
        attempts["count"] += 1
        raise RuntimeError("persistent audio failure")

    monkeypatch.setattr(ai_client.time, "sleep", lambda _: None)

    with caplog.at_level(logging.WARNING):
        result = ai_client._retry_with_backoff(
            failing_operation,
            "Test audio operation",
        )

    assert result is None
    assert attempts["count"] == ai_client.AUDIO_MAX_RETRIES
    assert "failed after" in caplog.text
