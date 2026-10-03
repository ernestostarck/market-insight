from __future__ import annotations

from typing import Any

import httpx
import pytest
from app.integrations.chilecompra.client import ChileCompraHTTPClient
from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.exceptions import ChileCompraTimeoutError


class MockResponse:
    def __init__(self, status_code: int = 200, payload: Any | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.headers = {"content-type": "application/json"}
        self.text = "{}"

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://example.test"),
                response=httpx.Response(self.status_code),
            )


class MockAsyncClient:
    def __init__(self, response: MockResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def request(self, method: str, path: str, params=None, json=None):
        self.calls.append(
            {"method": method, "path": path, "params": params, "json": json}
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.mark.asyncio
async def test_client_adds_ticket_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    config = ChileCompraConfig(
        api_url="https://api.mercadopublico.cl/servicios/v1/publico",
        api_ticket="ticket-123",
    )
    mock_client = MockAsyncClient(MockResponse())

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = ChileCompraHTTPClient(config)
    response = await client.request(
        "GET", "/licitaciones.json", params={"codigo": "123"}
    )

    assert response.status_code == 200
    assert mock_client.calls[0]["params"] == {"ticket": "ticket-123", "codigo": "123"}


@pytest.mark.asyncio
async def test_client_raises_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    config = ChileCompraConfig(
        api_url="https://api.mercadopublico.cl/servicios/v1/publico",
        api_ticket="ticket-123",
    )
    mock_client = MockAsyncClient(httpx.TimeoutException("timeout"))

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = ChileCompraHTTPClient(config)

    with pytest.raises(ChileCompraTimeoutError):
        await client.request("GET", "/licitaciones.json")
