from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.schemas.search import SearchQuery
from app.services.search import SearchService


class _Licitaciones:
    async def search_by_text(self, query: str, limit: int):
        assert query == "hospital central"
        assert limit == 5
        return [
            SimpleNamespace(
                id=11,
                nombre="Hospital Central",
                codigo="LC-11",
                estado="publicada",
                organismo_id=8,
                monto_estimado=1250,
                es_adjudicada=False,
            )
        ]


class _Proveedores:
    async def search_by_razon_social(self, query: str, limit: int):
        return [
            SimpleNamespace(
                id=4,
                razon_social="Central SPA",
                nombre_fantasia=None,
                rut="76.123.456-7",
                region="Metropolitana",
                estado="activo",
            )
        ]


class _Organismos:
    async def search_by_nombre(self, query: str, limit: int):
        return []


def test_search_returns_typed_results_across_requested_entities() -> None:
    service = SearchService(_Licitaciones(), _Proveedores(), _Organismos())

    response = asyncio.run(
        service.search(
            SearchQuery(
                query="  hospital   central ",
                entities={"licitacion", "proveedor"},
                limit_per_entity=5,
            )
        )
    )

    assert response.query == "hospital central"
    assert response.total == 2
    assert [result.entity_type for result in response.results] == [
        "licitacion",
        "proveedor",
    ]
    assert response.results[0].metadata["monto_estimado"] == 1250.0


def test_search_query_rejects_whitespace_only_input() -> None:
    try:
        SearchQuery(query="   ")
    except ValueError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("SearchQuery must reject a whitespace-only query")


def test_search_query_requires_an_entity() -> None:
    try:
        SearchQuery(query="compras", entities=set())
    except ValueError as exc:
        assert "at least one entity" in str(exc)
    else:
        raise AssertionError("SearchQuery must reject an empty entity selection")
