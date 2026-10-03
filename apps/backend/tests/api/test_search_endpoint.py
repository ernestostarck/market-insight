from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.dependencies import get_current_user, get_search_service
from app.main import app
from app.schemas.search import SearchResponse, SearchResult


class _SearchServiceStub:
    async def search(self, request):
        return SearchResponse(
            query=request.query,
            entities=request.entities,
            total=1,
            results=[
                SearchResult(
                    entity_type="licitacion",
                    id=7,
                    title="Compra de equipos médicos",
                    code="LC-7",
                )
            ],
        )


def _client() -> TestClient:
    app.dependency_overrides[get_search_service] = _SearchServiceStub
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        email="test@example.com", is_active=True
    )
    return TestClient(app)


def test_search_endpoint_returns_federated_response() -> None:
    response = _client().get(
        "/api/v1/search",
        params=[("q", "  equipos   médicos "), ("entity", "licitacion")],
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "equipos médicos",
        "entities": ["licitacion"],
        "total": 1,
        "results": [
            {
                "entity_type": "licitacion",
                "id": 7,
                "title": "Compra de equipos médicos",
                "subtitle": None,
                "code": "LC-7",
                "metadata": {},
            }
        ],
    }


def test_search_endpoint_validates_query_and_limit() -> None:
    client = _client()

    assert client.get("/api/v1/search", params={"q": "x"}).status_code == 422
    assert (
        client.get("/api/v1/search", params={"q": "equipos", "limit_per_entity": 51}).status_code
        == 422
    )
