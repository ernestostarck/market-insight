from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.dependencies import get_analytics_repository, get_current_user
from app.main import app


class _AnalyticsRepositoryStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def market_monthly(self, **kwargs):
        self.calls.append(("market_monthly", kwargs))
        return [
            SimpleNamespace(
                mes=date(2026, 8, 1),
                total_licitaciones=12,
                total_adjudicaciones=8,
                monto_total_adjudicado=Decimal("1250000.00"),
            )
        ]

    async def supplier_performance(self, **kwargs):
        self.calls.append(("supplier_performance", kwargs))
        return [
            SimpleNamespace(
                razon_social="Suministros Medicos del Sur SpA",
                rut="76.123.456-7",
                total_adjudicaciones=5,
                monto_total_adjudicado=Decimal("9800000.00"),
                ratio_adjudicacion_promedio=Decimal("0.85"),
                ultima_adjudicacion=date(2026, 7, 15),
            )
        ]

    async def category_spending(self, **kwargs):
        self.calls.append(("category_spending", kwargs))
        return [
            SimpleNamespace(
                categoria="Equipamiento medico",
                codigo_categoria="42192000",
                gasto_total_oc=Decimal("5000000.00"),
                numero_ordenes_compra=20,
                gasto_promedio_oc=Decimal("250000.00"),
            )
        ]

    async def disability_contracts(self, **kwargs):
        self.calls.append(("disability_contracts", kwargs))
        return [
            SimpleNamespace(
                licitacion_id="1000-01-LR26",
                nombre="Sillas de ruedas",
                descripcion="Compra de sillas de ruedas para centros geriatricos",
                monto_adjudicado=Decimal("3000000.00"),
                proveedor="Suministros Medicos del Sur SpA",
                organismo="Servicio de Salud Metropolitano Sur",
                periodo=date(2026, 7, 1),
            )
        ]

    async def data_quality_missing_keys(self):
        self.calls.append(("data_quality_missing_keys", {}))
        return [SimpleNamespace(fact_table="fact_licitacion", missing_count=3)]


def _client(repository: _AnalyticsRepositoryStub | None = None) -> tuple[TestClient, _AnalyticsRepositoryStub]:
    app.dependency_overrides.clear()
    repository = repository or _AnalyticsRepositoryStub()
    app.dependency_overrides[get_analytics_repository] = lambda: repository
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        email="test@example.com", is_active=True
    )
    return TestClient(app), repository


def test_market_monthly_analytics_endpoint() -> None:
    client, _ = _client()

    response = client.get(
        "/api/v1/analytics/market/monthly",
        params={"start_month": "2026-01-01", "limit": 10},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "mes": "2026-08-01",
            "total_licitaciones": 12,
            "total_adjudicaciones": 8,
            "monto_total_adjudicado": "1250000.00",
        }
    ]


def test_market_monthly_rejects_inverted_range() -> None:
    client, _ = _client()

    response = client.get(
        "/api/v1/analytics/market/monthly",
        params={"start_month": "2026-08-01", "end_month": "2026-01-01"},
    )

    assert response.status_code == 422


def test_supplier_performance_endpoint_returns_data_and_forwards_filters() -> None:
    client, repository = _client()

    response = client.get(
        "/api/v1/analytics/suppliers/performance",
        params={"query": "Suministros", "min_awarded_amount": 100000, "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["razon_social"] == "Suministros Medicos del Sur SpA"
    assert payload[0]["rut"] == "76.123.456-7"
    call = dict(repository.calls[0][1])
    assert call["query"] == "Suministros"
    assert call["min_awarded_amount"] == 100000.0


def test_supplier_performance_rejects_too_short_query() -> None:
    client, _ = _client()

    response = client.get("/api/v1/analytics/suppliers/performance", params={"query": "a"})

    assert response.status_code == 422


def test_category_spending_endpoint_returns_data() -> None:
    client, repository = _client()

    response = client.get(
        "/api/v1/analytics/categories/spending",
        params={"category_code": "42192000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["categoria"] == "Equipamiento medico"
    assert repository.calls[0] == (
        "category_spending",
        {"category_code": "42192000", "licitacion_ids": None, "offset": 0, "limit": 100},
    )


def test_disability_contracts_endpoint_returns_data() -> None:
    client, _ = _client()

    response = client.get(
        "/api/v1/analytics/disability/contracts",
        params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["licitacion_id"] == "1000-01-LR26"
    assert payload[0]["organismo"] == "Servicio de Salud Metropolitano Sur"


def test_disability_contracts_rejects_inverted_date_range() -> None:
    client, _ = _client()

    response = client.get(
        "/api/v1/analytics/disability/contracts",
        params={"start_date": "2026-08-10", "end_date": "2026-08-01"},
    )

    assert response.status_code == 422


def test_quality_missing_keys_endpoint_returns_data() -> None:
    client, _ = _client()

    response = client.get("/api/v1/analytics/quality/missing-keys")

    assert response.status_code == 200
    assert response.json() == [{"fact_table": "fact_licitacion", "missing_count": 3}]


def test_analytics_endpoints_require_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_analytics_repository] = lambda: _AnalyticsRepositoryStub()
    client = TestClient(app)

    response = client.get("/api/v1/analytics/quality/missing-keys")

    assert response.status_code == 401
    app.dependency_overrides.clear()
