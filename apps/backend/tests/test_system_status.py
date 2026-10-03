from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_system_status_endpoint() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()

        # Check required top-level attributes
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data
        assert "etl" in data
        assert "data_quality" in data

        # Check individual component keys
        components = data["components"]
        assert "api" in components
        assert "postgres" in components
        assert "redis" in components
        assert "minio" in components
        assert "chilecompra" in components

        # Check ETL and Data Quality details
        assert "status" in data["etl"]
        assert "score" in data["data_quality"]
        assert 0.0 <= data["data_quality"]["score"] <= 100.0


@pytest.mark.asyncio
async def test_system_status_root_alias() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/system/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
