from __future__ import annotations

from app.etl.enrichment.licitacion_detail import enrich_licitacion_detail
from app.etl.models import IngestionRunContext, LoadResult, TransformedRecord


class FakeLicitacionesResource:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[str] = []

    async def detalle_raw(self, codigo: str) -> dict:
        self.calls.append(codigo)
        return self._payload


class FakeClient:
    def __init__(self, payload: dict) -> None:
        self.licitaciones = FakeLicitacionesResource(payload)


class FakeLicitacionLoader:
    def __init__(self) -> None:
        self.loaded: list[tuple[IngestionRunContext, list[TransformedRecord]]] = []

    def load(self, run: IngestionRunContext, records: list[TransformedRecord]) -> LoadResult:
        self.loaded.append((run, records))
        return LoadResult(inserted=len(records))


class FakeItemLoader:
    def __init__(self, items_upserted: int = 0) -> None:
        self._items_upserted = items_upserted
        self.calls: list[dict] = []

    def upsert_items(self, connection, *, licitacion_codigo: str, items) -> int:
        self.calls.append({"connection": connection, "codigo": licitacion_codigo, "items": items})
        return self._items_upserted


_DETAIL_PAYLOAD = {
    "Listado": [
        {
            "CodigoExterno": "1002588-89-LE26",
            "Descripcion": "Adquirir materiales e insumos.",
            "Comprador": {"CodigoOrganismo": "701", "NombreOrganismo": "Servicio Nacional"},
            "Fechas": {"FechaPublicacion": "2026-08-10T13:45:28.563", "FechaCierre": "2026-08-20T14:23:00"},
            "Items": {"Listado": [{"Correlativo": 1, "NombreProducto": "Tul", "Cantidad": 1.0}]},
        }
    ]
}


async def test_enrich_persists_descripcion_organismo_and_items() -> None:
    client = FakeClient(_DETAIL_PAYLOAD)
    licitacion_loader = FakeLicitacionLoader()
    item_loader = FakeItemLoader(items_upserted=1)
    closed = []
    committed = []

    result = await enrich_licitacion_detail(
        "1002588-89-LE26",
        client=client,
        licitacion_loader=licitacion_loader,
        item_loader=item_loader,
        connection_factory=lambda: _FakeConnection(closed, committed),
    )

    assert result.found is True
    assert result.items_upserted == 1
    assert client.licitaciones.calls == ["1002588-89-LE26"]

    [(run, records)] = licitacion_loader.loaded
    assert run.resource == "licitaciones"
    record = records[0]
    assert record.payload["descripcion"] == "Adquirir materiales e insumos."
    assert record.payload["agency_code"] == "701"
    assert record.payload["agency_name"] == "Servicio Nacional"
    assert record.natural_key == "chilecompra:licitacion:1002588-89-LE26"

    assert item_loader.calls[0]["codigo"] == "1002588-89-LE26"
    assert len(item_loader.calls[0]["items"]) == 1
    assert closed == [True]


async def test_enrich_commits_the_item_connection() -> None:
    """Regression: found against real data (6.13) — the items connection
    was closed without ever calling commit(), so items silently never
    persisted against a real Postgres connection."""
    client = FakeClient(_DETAIL_PAYLOAD)
    committed: list[bool] = []

    await enrich_licitacion_detail(
        "1002588-89-LE26",
        client=client,
        licitacion_loader=FakeLicitacionLoader(),
        item_loader=FakeItemLoader(items_upserted=1),
        connection_factory=lambda: _FakeConnection([], committed),
    )

    assert committed == [True]


async def test_enrich_returns_not_found_without_touching_loaders() -> None:
    client = FakeClient({"Listado": []})
    licitacion_loader = FakeLicitacionLoader()
    item_loader = FakeItemLoader()

    result = await enrich_licitacion_detail(
        "unknown-codigo",
        client=client,
        licitacion_loader=licitacion_loader,
        item_loader=item_loader,
        connection_factory=lambda: (_ for _ in ()).throw(AssertionError("should not open a connection")),
    )

    assert result.found is False
    assert result.items_upserted == 0
    assert licitacion_loader.loaded == []
    assert item_loader.calls == []


class _FakeConnection:
    def __init__(self, closed: list[bool], committed: list[bool] | None = None) -> None:
        self._closed = closed
        self._committed = committed if committed is not None else []

    def commit(self) -> None:
        self._committed.append(True)

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self._closed.append(True)
