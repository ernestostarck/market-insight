from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import AppException, register_exception_handlers
from app.integrations.chilecompra.exceptions import (
    ChileCompraAuthenticationError,
    ChileCompraNotFoundError,
    ChileCompraRateLimitError,
    ChileCompraTimeoutError,
    ChileCompraValidationError,
)


class _Body(BaseModel):
    value: int


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/app-exception")
    def raise_app_exception():
        raise AppException("nope", code="CUSTOM_ERROR", status_code=403)

    @app.get("/boom/app-exception-500")
    def raise_app_exception_500():
        raise AppException("internal", code="INTERNAL_ISSUE", status_code=500)

    @app.post("/boom/validate")
    def raise_validation(body: _Body):
        return {"value": body.value}

    @app.get("/boom/chilecompra-not-found")
    def raise_not_found():
        raise ChileCompraNotFoundError("resource missing")

    @app.get("/boom/chilecompra-validation")
    def raise_chilecompra_validation():
        raise ChileCompraValidationError("bad query")

    @app.get("/boom/chilecompra-auth")
    def raise_chilecompra_auth():
        raise ChileCompraAuthenticationError("bad ticket")

    @app.get("/boom/chilecompra-rate-limit")
    def raise_chilecompra_rate_limit():
        raise ChileCompraRateLimitError("slow down")

    @app.get("/boom/chilecompra-timeout")
    def raise_chilecompra_timeout():
        raise ChileCompraTimeoutError("too slow")

    @app.get("/boom/unhandled")
    def raise_unhandled():
        raise RuntimeError("totally unexpected")

    return app


def test_app_exception_uses_declared_status_and_code() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/app-exception")

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "CUSTOM_ERROR", "message": "nope", "request_id": None}
    }


def test_app_exception_survives_500_without_leaking_stack_trace() -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom/app-exception-500")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ISSUE"


def test_validation_error_returns_422_with_details() -> None:
    client = TestClient(_build_app())

    response = client.post("/boom/validate", json={"value": "not-an-int"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "value" in body["error"]["message"]


def test_chilecompra_not_found_maps_to_502() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/chilecompra-not-found")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "CHILECOMPRA_NOT_FOUND"


def test_chilecompra_validation_maps_to_422() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/chilecompra-validation")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHILECOMPRA_VALIDATION_ERROR"


def test_chilecompra_auth_maps_to_502() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/chilecompra-auth")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "CHILECOMPRA_AUTH_ERROR"


def test_chilecompra_rate_limit_maps_to_429() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/chilecompra-rate-limit")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "CHILECOMPRA_RATE_LIMIT"


def test_chilecompra_timeout_maps_to_504() -> None:
    client = TestClient(_build_app())

    response = client.get("/boom/chilecompra-timeout")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "CHILECOMPRA_TIMEOUT"


def test_unhandled_exception_returns_generic_500_without_leaking_details() -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom/unhandled")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "RuntimeError" not in body["error"]["message"]
    assert "totally unexpected" not in body["error"]["message"]


def test_unhandled_exception_is_logged_with_traceback(caplog) -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)

    with caplog.at_level("ERROR", logger="app.core.exceptions"):
        client.get("/boom/unhandled")

    assert any("Unhandled exception" in record.message for record in caplog.records)
    assert any(record.exc_info for record in caplog.records)
