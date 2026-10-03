from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.dependencies import get_current_user
from app.main import app


def _authed_client() -> TestClient:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        email="test@example.com", is_active=True
    )
    return TestClient(app)


def test_taxonomy_endpoint_lists_every_sector_including_apparel() -> None:
    client = _authed_client()

    response = client.get("/api/v1/nlp/taxonomy")

    assert response.status_code == 200
    payload = response.json()
    codes = {c["code"] for c in payload["categories"]}
    assert "apparel" in codes
    assert "health" in codes


def test_taxonomy_endpoint_apparel_category_has_shapewear_concepts() -> None:
    client = _authed_client()

    payload = client.get("/api/v1/nlp/taxonomy").json()

    apparel = next(c for c in payload["categories"] if c["code"] == "apparel")
    assert apparel["name"]
    shapewear = next(s for s in apparel["subcategories"] if s["code"] == "shapewear")
    concept_codes = {c["code"] for c in shapewear["concepts"]}
    assert concept_codes == {"faja_reductora", "faja_moldeadora_short", "faja_moldeadora_colaless"}


def test_taxonomy_endpoint_requires_authentication() -> None:
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.get("/api/v1/nlp/taxonomy")

    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_classify_endpoint_recognizes_shapewear_text() -> None:
    client = _authed_client()

    response = client.post(
        "/api/v1/nlp/classify",
        json={"text": "Faja body moldeadora tipo short sin costuras"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["category_code"] == "apparel"
    assert payload["subcategory_code"] == "shapewear"
