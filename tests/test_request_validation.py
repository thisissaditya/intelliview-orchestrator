import pytest
from fastapi import FastAPI, Request
from starlette.responses import Response

from orchestrator.request_validation import RequestValidationMiddleware


@pytest.fixture
def middleware():
    app = FastAPI()

    return RequestValidationMiddleware(
        app,
        max_body_size_bytes=1024,
        check_content_type=True,
        scan_for_dangerous_patterns=True,
    )


def make_request(path: str, query: str = "", method: str = "GET"):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query.encode(),
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }

    async def receive():
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }

    return Request(scope, receive)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malicious_input",
    [
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "onclick=alert(1)",
        "UNION SELECT username FROM users",
        "; DROP TABLE users",
        "__import__('os')",
        "eval('1+1')",
        "exec('print(1)')",
    ],
)
async def test_blocks_injection_patterns(middleware, malicious_input):
    request = make_request("/test", f"input={malicious_input}")

    async def call_next(request):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 400
    assert response.body == (
        b'{"detail":"Request contains invalid characters or patterns"}'
    )


@pytest.mark.asyncio
async def test_rejects_unsupported_content_type(middleware):
    request = make_request("/test", method="POST")
    request.scope["headers"] = [
        (b"content-type", b"application/xml"),
    ]

    async def call_next(request):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 415
    assert response.body == (b'{"detail":"Unsupported content-type: application/xml"}')


@pytest.mark.asyncio
async def test_rejects_oversized_request(middleware):
    request = make_request("/test", method="POST")
    request.scope["headers"] = [
        (b"content-type", b"application/json"),
        (b"content-length", b"2048"),
    ]

    async def call_next(request):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 413
    assert response.body == (
        b'{"detail":"Request body too large (2048 bytes, max 1024)"}'
    )


@pytest.mark.asyncio
async def test_ignores_malformed_content_length(middleware):
    request = make_request("/test", method="POST")
    request.scope["headers"] = [
        (b"content-type", b"application/json"),
        (b"content-length", b"not-a-number"),
    ]

    async def call_next(request):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert response.body == b"OK"


@pytest.mark.asyncio
async def test_allows_valid_request(middleware):
    request = make_request("/test", method="POST")
    request.scope["headers"] = [
        (b"content-type", b"application/json"),
        (b"content-length", b"100"),
    ]

    async def call_next(request):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert response.body == b"OK"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/ready",
        "/livez",
        "/docs",
        "/openapi.json",
    ],
)
async def test_skips_validation_for_health_and_docs_paths(middleware, path):
    request = make_request(
        path,
        query="input=<script>alert(1)</script>",
    )

    async def call_next(request):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert response.body == b"OK"
