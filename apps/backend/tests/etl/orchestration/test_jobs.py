"""Tests for the ETL orchestration jobs (Fase 3.11)."""

from __future__ import annotations

from app.etl.ingestion.raw_ingestor import SqlAlchemyRawIngestor
from app.etl.loading.core_schema import CoreLicitacionLoader
from app.etl.orchestration.jobs import (
    DEFAULT_RESOURCES,
    _pipeline_factory,
    _sync_one_resource,
    enrich_licitacion_detail,
    sync_all_resources,
)


class TestDefaultResources:
    def test_default_resources_cover_core_streams(self) -> None:
        assert "licitaciones" in DEFAULT_RESOURCES
        assert "ordenes_compra" in DEFAULT_RESOURCES
        assert "empresas" in DEFAULT_RESOURCES
        assert "contratos" in DEFAULT_RESOURCES
        assert "convenios_marco" in DEFAULT_RESOURCES
        assert "adjudicaciones" in DEFAULT_RESOURCES


class TestSyncOneResource:
    def test_rejects_unsupported_resource(self) -> None:
        try:
            _sync_one_resource(resource="no_such_resource")
        except ValueError as exc:
            assert "Unsupported resource" in str(exc)
            return
        raise AssertionError("Expected ValueError for unsupported resource")


class TestPipelineFactory:
    def test_licitaciones_pipeline_uses_real_core_loader_and_raw_ingestor(self) -> None:
        pipeline = _pipeline_factory("licitaciones")()

        assert isinstance(pipeline.loader, CoreLicitacionLoader)
        assert isinstance(pipeline.raw_ingestor, SqlAlchemyRawIngestor)

    def test_other_resources_keep_the_in_memory_loader(self) -> None:
        pipeline = _pipeline_factory("empresas")()

        assert not isinstance(pipeline.loader, CoreLicitacionLoader)
        assert isinstance(pipeline.raw_ingestor, SqlAlchemyRawIngestor)


class TestEnrichLicitacionDetail:
    def test_task_is_registered_on_celery_app(self) -> None:
        assert enrich_licitacion_detail.name == "app.etl.orchestration.jobs.enrich_licitacion_detail"


class TestSyncAllResources:
    def test_sync_all_returns_per_resource_results(self, monkeypatch) -> None:
        def fake_sync_one(**kwargs) -> dict[str, object]:
            return {
                "status": "succeeded",
                "run_id": "run-1",
                "source": "chilecompra_api",
                "resource": kwargs.get("resource"),
                "metrics": {"valid": 10},
                "error": None,
            }

        monkeypatch.setattr(
            "app.etl.orchestration.jobs._sync_one_resource",
            fake_sync_one,
        )

        result = sync_all_resources(resources=("licitaciones", "empresas"))

        assert result["source"] == "chilecompra_api"
        assert result["resources"]["licitaciones"]["status"] == "succeeded"
        assert result["resources"]["empresas"]["resource"] == "empresas"
