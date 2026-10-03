from __future__ import annotations

import uuid

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.context import get_request_id
from app.core.middleware import RequestIDMiddleware


async def _echo(request: Request):
    return JSONResponse(
        {
            "state_request_id": getattr(request.state, "request_id", None),
            "contextvar_request_id": get_request_id(),
        }
    )


def _build_client() -> TestClient:
    inner = Starlette(routes=[Route("/echo", _echo)])
    app = RequestIDMiddleware(inner)
    return TestClient(app)


def test_generates_a_request_id_when_none_provided() -> None:
    client = _build_client()

    response = client.get("/echo")

    request_id = response.headers["x-request-id"]
    uuid.UUID(request_id)  # raises ValueError if not a valid UUID


def test_echoes_a_provided_request_id() -> None:
    client = _build_client()

    response = client.get("/echo", headers={"X-Request-ID": "my-custom-id"})

    assert response.headers["x-request-id"] == "my-custom-id"


def test_sets_request_state_and_contextvar_during_the_request() -> None:
    client = _build_client()

    response = client.get("/echo", headers={"X-Request-ID": "abc-123"})

    body = response.json()
    assert body["state_request_id"] == "abc-123"
    assert body["contextvar_request_id"] == "abc-123"


def test_contextvar_is_reset_after_the_request_completes() -> None:
    client = _build_client()

    client.get("/echo", headers={"X-Request-ID": "leaky-id"})

    assert get_request_id() == ""


def test_includes_process_time_header() -> None:
    client = _build_client()

    response = client.get("/echo")

    duration = float(response.headers["x-process-time-ms"])
    assert duration >= 0


def test_emits_a_structured_access_log_line(caplog) -> None:
    client = _build_client()

    with caplog.at_level("INFO", logger="app.access"):
        client.get("/echo", headers={"X-Request-ID": "log-test-id"})

    records = [r for r in caplog.records if r.name == "app.access"]
    assert len(records) == 1
    record = records[0]
    assert record.http_method == "GET"
    assert record.http_path == "/echo"
    assert record.http_status_code == 200
    assert record.duration_ms >= 0
