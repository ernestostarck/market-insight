from __future__ import annotations

from datetime import date
from typing import Any, Self

import httpx
import pytest
from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.exceptions import (
    ChileCompraNotFoundError,
    ChileCompraValidationError,
)
from app.integrations.chilecompra.sdk import ChileCompraClient


class MockResponse:
    def __init__(self, status_code: int = 200, payload: Any | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"Listado": []}
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
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def request(self, method: str, path: str, params=None, json=None):
        self.calls.append(
            {"method": method, "path": path, "params": params, "json": json}
        )
        return MockResponse(payload={"Listado": [{"CodigoExterno": "1000-1-LP26"}]})


@pytest.mark.asyncio
async def test_sdk_exposes_resource_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    config = ChileCompraConfig(
        api_url="https://api.mercadopublico.cl/servicios/v1/publico",
        api_ticket="ticket-123",
    )
    sdk = ChileCompraClient.from_config(config)

    payload = await sdk.licitaciones.por_codigo("1000-1-LP26")

    assert payload.cantidad == 1
    assert payload.listado[0].codigo_externo == "1000-1-LP26"
    assert mock_client.calls[0]["path"] == "/licitaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "codigo": "1000-1-LP26",
    }


@pytest.mark.asyncio
async def test_licitaciones_detalle_raw_returns_full_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    payload = await sdk.licitaciones.detalle_raw("1000-1-LP26")

    assert payload == {"Listado": [{"CodigoExterno": "1000-1-LP26"}]}
    assert mock_client.calls[0]["path"] == "/licitaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "codigo": "1000-1-LP26",
    }


def test_sdk_builds_from_config() -> None:
    config = ChileCompraConfig(
        api_url="https://api.mercadopublico.cl/servicios/v1/publico",
        api_ticket="ticket-123",
        timeout=45,
        max_retries=5,
        retry_delay=1.0,
    )

    sdk = ChileCompraClient.from_config(config)

    assert sdk is not None
    assert sdk.licitaciones is not None
    assert sdk.ordenes_compra is not None
    assert sdk.empresas is not None
    assert sdk.contratos is not None
    assert sdk.convenios_marco is not None
    assert sdk.adjudicaciones is not None


@pytest.mark.asyncio
async def test_licitaciones_por_fecha_normalizes_yyyymmdd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.licitaciones.por_fecha("20260806")

    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_licitaciones_por_fecha_accepts_date_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.licitaciones.por_fecha(date(2026, 8, 6))

    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_licitaciones_por_codigo_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.licitaciones.por_codigo("codigo invalido")


@pytest.mark.asyncio
async def test_ordenes_compra_por_fecha_normalizes_yyyymmdd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.ordenes_compra.por_fecha("20260806")

    assert mock_client.calls[0]["path"] == "/ordenesdecompra.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_ordenes_compra_por_fecha_accepts_date_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.ordenes_compra.por_fecha(date(2026, 8, 6))

    assert mock_client.calls[0]["path"] == "/ordenesdecompra.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_ordenes_compra_por_codigo_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.ordenes_compra.por_codigo("codigo invalido")


@pytest.mark.asyncio
async def test_empresas_buscar_proveedor_normalizes_rut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.empresas.buscar_proveedor("76.123.456-7")

    assert mock_client.calls[0]["path"] == "/empresas.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "rut": "76123456-7",
    }


@pytest.mark.asyncio
async def test_empresas_buscar_compradores_uses_tipo_param(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.empresas.buscar_compradores()

    assert mock_client.calls[0]["path"] == "/empresas.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "tipo": "compradores",
    }


@pytest.mark.asyncio
async def test_empresas_buscar_proveedor_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.empresas.buscar_proveedor("rut invalido")


@pytest.mark.asyncio
async def test_contratos_por_fecha_normalizes_yyyymmdd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.contratos.por_fecha("20260806")

    assert mock_client.calls[0]["path"] == "/contratos.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_contratos_por_fecha_accepts_date_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.contratos.por_fecha(date(2026, 8, 6))

    assert mock_client.calls[0]["path"] == "/contratos.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_contratos_por_codigo_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.contratos.por_codigo("codigo invalido")


@pytest.mark.asyncio
async def test_convenios_marco_por_fecha_normalizes_yyyymmdd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.convenios_marco.por_fecha("20260806")

    assert mock_client.calls[0]["path"] == "/conveniomarco.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_convenios_marco_por_fecha_accepts_date_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.convenios_marco.por_fecha(date(2026, 8, 6))

    assert mock_client.calls[0]["path"] == "/conveniomarco.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_convenios_marco_por_codigo_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.convenios_marco.por_codigo("codigo invalido")


@pytest.mark.asyncio
async def test_adjudicaciones_por_fecha_normalizes_yyyymmdd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.adjudicaciones.por_fecha("20260806")

    assert mock_client.calls[0]["path"] == "/adjudicaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_adjudicaciones_por_fecha_accepts_date_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.adjudicaciones.por_fecha(date(2026, 8, 6))

    assert mock_client.calls[0]["path"] == "/adjudicaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_adjudicaciones_buscar_avanzado_normalizes_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    await sdk.adjudicaciones.buscar_avanzado(
        {
            "estado": "vigente",
            "proveedor_rut": "76.123.456-7",
            "page": 2,
            "page_size": 20,
        }
    )

    assert mock_client.calls[0]["path"] == "/adjudicaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "page": "2",
        "page_size": "20",
        "estado": "VIGENTE",
        "proveedorRut": "76123456-7",
    }


@pytest.mark.asyncio
async def test_adjudicaciones_buscar_avanzado_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.adjudicaciones.buscar_avanzado(
            {
                "page": 0,
                "page_size": 1000,
            }
        )


@pytest.mark.asyncio
async def test_adjudicaciones_por_codigo_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraValidationError):
        await sdk.adjudicaciones.por_codigo("codigo invalido")


@pytest.mark.asyncio
async def test_adjudicaciones_analisis_oportunidad_por_fecha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    result = await sdk.adjudicaciones.analisis_oportunidad_por_fecha("20260806")

    assert result.summary.total_items == 1
    assert mock_client.calls[0]["path"] == "/adjudicaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "fecha": "06082026",
    }


@pytest.mark.asyncio
async def test_adjudicaciones_analisis_oportunidad_busqueda_avanzada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    result = await sdk.adjudicaciones.analisis_oportunidad_busqueda_avanzada(
        {"estado": "adjudicada", "page": 1, "page_size": 10}
    )

    assert result.summary.scored_items == 1
    assert mock_client.calls[0]["path"] == "/adjudicaciones.json"
    assert mock_client.calls[0]["params"] == {
        "ticket": "ticket-123",
        "page": "1",
        "page_size": "10",
        "estado": "ADJUDICADA",
    }


@pytest.mark.asyncio
async def test_adjudicaciones_por_fecha_falls_back_to_licitaciones_when_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FallbackMockAsyncClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(self, method: str, path: str, params=None, json=None):
            self.calls.append(
                {"method": method, "path": path, "params": params, "json": json}
            )
            if path == "/adjudicaciones.json":
                return MockResponse(status_code=404, payload={"Codigo": 404})
            return MockResponse(payload={"Listado": [{"CodigoExterno": "1000-1-LP26"}]})

    mock_client = FallbackMockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    payload = await sdk.adjudicaciones.por_fecha("20260806")

    assert payload.cantidad == 1
    assert [call["path"] for call in mock_client.calls] == [
        "/adjudicaciones.json",
        "/licitaciones.json",
    ]


@pytest.mark.asyncio
async def test_adjudicaciones_raises_not_found_when_primary_and_fallback_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NotFoundMockAsyncClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(self, method: str, path: str, params=None, json=None):
            self.calls.append(
                {"method": method, "path": path, "params": params, "json": json}
            )
            return MockResponse(status_code=404, payload={"Codigo": 404})

    mock_client = NotFoundMockAsyncClient()

    def fake_async_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    sdk = ChileCompraClient.from_config(
        ChileCompraConfig(
            api_url="https://api.mercadopublico.cl/servicios/v1/publico",
            api_ticket="ticket-123",
        )
    )

    with pytest.raises(ChileCompraNotFoundError):
        await sdk.adjudicaciones.por_fecha("20260806")

    assert [call["path"] for call in mock_client.calls] == [
        "/adjudicaciones.json",
        "/licitaciones.json",
    ]
