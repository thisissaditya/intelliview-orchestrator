import json
from datetime import datetime, timezone

from orchestrator.utils import (
    is_coroutine,
    log_event,
    redis_json_get,
    redis_json_set,
    utc_now_iso,
)


def test_utc_now_iso_returns_utc_iso_timestamp():
    result = utc_now_iso()

    parsed = datetime.fromisoformat(result)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


async def async_function():
    pass


def regular_function():
    pass


def test_is_coroutine_returns_true_for_async_function():
    assert is_coroutine(async_function) is True


def test_is_coroutine_returns_false_for_regular_function():
    assert is_coroutine(regular_function) is False


def test_redis_json_get_returns_none_for_none_client():
    assert redis_json_get(None, "key") is None


def test_redis_json_get_decodes_json():
    client = type("Client", (), {"get": lambda self, key: '{"name": "Vidhi"}'})()

    assert redis_json_get(client, "key") == {"name": "Vidhi"}


def test_redis_json_get_returns_none_for_missing_value():
    client = type("Client", (), {"get": lambda self, key: None})()

    assert redis_json_get(client, "key") is None


def test_redis_json_get_returns_none_when_redis_raises():
    def get(_self, _key):
        raise RuntimeError("Redis unavailable")

    client = type("Client", (), {"get": get})()

    assert redis_json_get(client, "key") is None


def test_redis_json_get_returns_none_for_invalid_json():
    client = type("Client", (), {"get": lambda self, key: "not-json"})()

    assert redis_json_get(client, "key") is None


def test_redis_json_set_returns_false_for_none_client():
    assert redis_json_set(None, "key", {"value": 1}) is False


def test_redis_json_set_stores_json_without_ttl():
    calls = []

    class Client:
        def set(self, *args, **kwargs):
            calls.append((args, kwargs))

    client = Client()

    assert redis_json_set(client, "key", {"value": 1}) is True
    assert calls == [(("key", json.dumps({"value": 1})), {})]


def test_redis_json_set_stores_json_with_ttl():
    calls = []

    class Client:
        def set(self, *args, **kwargs):
            calls.append((args, kwargs))

    client = Client()

    assert redis_json_set(client, "key", {"value": 1}, ttl=60) is True
    assert calls == [(("key", json.dumps({"value": 1})), {"ex": 60})]


def test_redis_json_set_returns_false_when_redis_raises():
    class Client:
        def set(self, *args, **kwargs):
            raise RuntimeError("Redis unavailable")

    client = Client()

    assert redis_json_set(client, "key", {"value": 1}) is False


def test_redis_json_set_uses_string_conversion_for_non_json_values():
    calls = []

    class Client:
        def set(self, *args, **kwargs):
            calls.append((args, kwargs))

    client = Client()
    value = object()

    assert redis_json_set(client, "key", value) is True
    assert calls[0][0] == ("key", json.dumps(value, default=str))


def test_log_event_passes_event_and_fields_to_logger():
    class Logger:
        def __init__(self):
            self.calls = []

        def log(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    logger = Logger()

    log_event(logger, 20, "test_event", user_id=123, status="ok")

    assert logger.calls == [
        (
            (20, "test_event"),
            {"extra": {"user_id": 123, "status": "ok"}},
        )
    ]
