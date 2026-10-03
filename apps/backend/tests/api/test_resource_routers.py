from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.pagination import encode_cursor
from app.db.dependencies import (
    get_adjudicacion_repository,
    get_categoria_service,
    get_comprador_service,
    get_contrato_service,
    get_current_user,
    get_licitacion_service,
    get_orden_de_compra_service,
    get_organismo_service,
    get_proveedor_service,
)
from app.main import app
from app.repositories.pagination import KeysetPage


class _FakeService:
    """Mimics *Service.page()/get() without touching a real repository/DB."""

    def __init__(self, items: list[SimpleNamespace]):
        self.items = items
        self.calls: list[dict] = []

    async def get(self, item_id: int):
        return next((item for item in self.items if item.id == item_id), None)

    async def page(
        self, *, limit: int, anchor_id: int | None = None, direction: str = "next", **_filters
    ):
        # `_filters` absorbs resource-specific extras (e.g. proveedores' q/region/rubro/
        # tasa_minima) that this generic fake doesn't need to honor.
        self.calls.append({"limit": limit, "anchor_id": anchor_id, "direction": direction})
        if direction == "next":
            window = [i for i in self.items if anchor_id is None or i.id > anchor_id]
            has_previous = anchor_id is not None and bool(window)
        else:
            window = [i for i in self.items if anchor_id is None or i.id < anchor_id]
            has_previous = False
        page_items = window[:limit]
        has_next = len(window) > limit if direction == "next" else bool(page_items)
        return KeysetPage(
            items=page_items,
            total=len(self.items),
            has_next=has_next,
            has_previous=has_previous,
        )


# (url prefix, resource name used for cursor signing, service dependency, sample item kwargs)
RESOURCES = [
    (
        "/licitaciones",
        "licitaciones",
        get_licitacion_service,
        dict(
            id=1,
            codigo="1234-56-LE26",
            nombre="Equipos de seguridad geriatrica",
            descripcion=None,
            estado="publicada",
            fecha_publicacion=None,
            fecha_cierre=None,
            monto_estimado=None,
            organismo_id=7,
            organismo=None,
        ),
    ),
    (
        "/proveedores",
        "proveedores",
        get_proveedor_service,
        dict(id=1, rut="76.123.456-7", razon_social="Suministros SpA", nombre_fantasia=None),
    ),
    (
        "/categorias",
        "categorias",
        get_categoria_service,
        dict(id=1, codigo="42192200", nombre="Sillas de Ruedas"),
    ),
    (
        "/organismos",
        "organismos",
        get_organismo_service,
        dict(id=1, codigo="H12345", nombre="Servicio de Salud Sur"),
    ),
    (
        "/compradores",
        "compradores",
        get_comprador_service,
        dict(id=1, name="Maria Perez", region="Metropolitana"),
    ),
    (
        "/contratos",
        "contratos",
        get_contrato_service,
        dict(id=1, title="Suministro de sillas de ruedas", amount=1000.0, start_date=None, end_date=None),
    ),
    (
        "/ordenes_de_compra",
        "ordenes_de_compra",
        get_orden_de_compra_service,
        dict(id=1, title="OC-2026-000512", amount=500.0, purchase_date=None),
    ),
]


def _authed_client(service_dep, fake: _FakeService) -> TestClient:
    app.dependency_overrides.clear()
    app.dependency_overrides[service_dep] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        email="test@example.com", is_active=True
    )
    return TestClient(app)


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_list_empty(prefix, resource, service_dep, sample) -> None:
    fake = _FakeService([])
    client = _authed_client(service_dep, fake)

    response = client.get(f"/api/v1{prefix}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["total"] == 0
    assert payload["has_next"] is False
    assert payload["next_cursor"] is None


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_list_returns_items_and_pagination_metadata(prefix, resource, service_dep, sample) -> None:
    items = [SimpleNamespace(**{**sample, "id": i}) for i in range(1, 4)]
    fake = _FakeService(items)
    client = _authed_client(service_dep, fake)

    response = client.get(f"/api/v1{prefix}/", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    assert payload["total"] == 3
    assert payload["has_next"] is True
    assert payload["next_cursor"] is not None
    assert fake.calls[0] == {"limit": 2, "anchor_id": None, "direction": "next"}


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_list_follows_next_cursor(prefix, resource, service_dep, sample) -> None:
    items = [SimpleNamespace(**{**sample, "id": i}) for i in range(1, 4)]
    fake = _FakeService(items)
    client = _authed_client(service_dep, fake)

    cursor = encode_cursor(resource, 2, "next")
    response = client.get(f"/api/v1{prefix}/", params={"limit": 2, "cursor": cursor})

    assert response.status_code == 200
    assert fake.calls[0] == {"limit": 2, "anchor_id": 2, "direction": "next"}


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_list_rejects_cursor_for_wrong_resource(prefix, resource, service_dep, sample) -> None:
    fake = _FakeService([])
    client = _authed_client(service_dep, fake)

    cursor = encode_cursor("some-other-resource", 2, "next")
    response = client.get(f"/api/v1{prefix}/", params={"cursor": cursor})

    assert response.status_code == 422


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_list_rejects_limit_out_of_bounds(prefix, resource, service_dep, sample) -> None:
    fake = _FakeService([])
    client = _authed_client(service_dep, fake)

    assert client.get(f"/api/v1{prefix}/", params={"limit": 0}).status_code == 422
    assert client.get(f"/api/v1{prefix}/", params={"limit": 101}).status_code == 422


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_get_by_id_found(prefix, resource, service_dep, sample) -> None:
    fake = _FakeService([SimpleNamespace(**sample)])
    client = _authed_client(service_dep, fake)

    response = client.get(f"/api/v1{prefix}/{sample['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == sample["id"]


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_get_by_id_not_found(prefix, resource, service_dep, sample) -> None:
    fake = _FakeService([])
    client = _authed_client(service_dep, fake)

    response = client.get(f"/api/v1{prefix}/999999")

    assert response.status_code == 404


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_list_requires_authentication(prefix, resource, service_dep, sample) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[service_dep] = lambda: _FakeService([])
    client = TestClient(app)

    response = client.get(f"/api/v1{prefix}/")

    assert response.status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.parametrize("prefix,resource,service_dep,sample", RESOURCES)
def test_get_by_id_requires_authentication(prefix, resource, service_dep, sample) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[service_dep] = lambda: _FakeService([])
    client = TestClient(app)

    response = client.get(f"/api/v1{prefix}/1")

    assert response.status_code == 401
    app.dependency_overrides.clear()


class _FakeRankingService:
    """Mimics *Service.ranking()/categoria_facets() for the server-sorted endpoints."""

    def __init__(self, items: list[dict], total: int):
        self.items = items
        self.total = total
        self.calls: list[dict] = []

    async def ranking(self, **kwargs):
        self.calls.append(kwargs)
        return self.items, self.total

    async def categoria_facets(self, *, licitacion_ids=None):
        return [("Equipamiento medico", 12), ("Obras civiles", 5)]


@pytest.mark.parametrize(
    "prefix,service_dep,item,sort_by",
    [
        (
            "/proveedores",
            get_proveedor_service,
            dict(id=1, rut="76.123.456-7", razon_social="Suministros SpA", monto_total_adjudicado=9.5e9),
            "total_adjudicaciones",
        ),
        (
            "/organismos",
            get_organismo_service,
            dict(id=7, codigo="H1", nombre="Hospital", total_licitaciones=40, monto_total_comprado=1e9),
            "total_licitaciones",
        ),
        (
            "/categorias",
            get_categoria_service,
            dict(id=3, codigo="42211500", nombre="Sillas de ruedas", monto_total=5e8),
            "total_proveedores",
        ),
    ],
)
def test_ranking_returns_server_sorted_offset_page(prefix, service_dep, item, sort_by) -> None:
    fake = _FakeRankingService([item], total=3146)
    client = _authed_client(service_dep, fake)

    response = client.get(
        f"/api/v1{prefix}/ranking", params={"limit": 10, "offset": 20, "sort_by": sort_by, "q": "x"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3146
    assert (body["offset"], body["limit"]) == (20, 10)
    assert body["data"][0]["id"] == item["id"]
    assert fake.calls[0]["limit"] == 10
    assert fake.calls[0]["offset"] == 20
    assert fake.calls[0]["sort_by"] == sort_by
    assert fake.calls[0]["sort_dir"] == "desc"
    assert fake.calls[0]["licitacion_ids"] is None
    app.dependency_overrides.clear()


@pytest.mark.parametrize("prefix,service_dep", [("/proveedores", get_proveedor_service), ("/organismos", get_organismo_service)])
def test_ranking_rejects_unknown_sort_field_and_oversized_page(prefix, service_dep) -> None:
    client = _authed_client(service_dep, _FakeRankingService([], total=0))

    assert client.get(f"/api/v1{prefix}/ranking", params={"sort_by": "dias_pago"}).status_code == 422
    assert client.get(f"/api/v1{prefix}/ranking", params={"limit": 500}).status_code == 422
    app.dependency_overrides.clear()


def test_proveedores_rubros_returns_real_category_facets() -> None:
    client = _authed_client(get_proveedor_service, _FakeRankingService([], total=0))

    response = client.get("/api/v1/proveedores/rubros")

    assert response.status_code == 200
    assert response.json() == [
        {"value": "Equipamiento medico", "count": 12},
        {"value": "Obras civiles", "count": 5},
    ]
    app.dependency_overrides.clear()


class _FakeAdjudicacionRepository:
    def __init__(self):
        self.calls: list[dict] = []

    async def get_ranking(self, **kwargs):
        self.calls.append(kwargs)
        return [
            dict(
                id=11,
                licitacion_id=5,
                licitacion_codigo="1234-5-LE26",
                licitacion_nombre="Sillas de ruedas",
                proveedor_id=8,
                proveedor_rut="76.123.456-7",
                proveedor_razon_social="Ortopedia SpA",
                organismo_id=2,
                organismo_nombre="Hospital",
                monto_adjudicado=1.5e7,
                fecha_adjudicacion="2026-05-01T00:00:00",
                desviacion_precio_referencial=-4.0,
            )
        ], 7249


def test_adjudicaciones_lists_real_awards_server_sorted() -> None:
    fake = _FakeAdjudicacionRepository()
    client = _authed_client(get_adjudicacion_repository, fake)

    response = client.get(
        "/api/v1/adjudicaciones",
        params={"limit": 25, "sort_by": "monto_adjudicado", "q": "hospital", "monto_min": 1e6},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 7249
    assert body["data"][0]["proveedor_razon_social"] == "Ortopedia SpA"
    assert fake.calls[0] | {"licitacion_ids": None} == {
        "limit": 25,
        "offset": 0,
        "sort_by": "monto_adjudicado",
        "sort_dir": "desc",
        "q": "hospital",
        "monto_min": 1e6,
        "licitacion_ids": None,
    }
    assert client.get("/api/v1/adjudicaciones", params={"sort_by": "nope"}).status_code == 422
    app.dependency_overrides.clear()
