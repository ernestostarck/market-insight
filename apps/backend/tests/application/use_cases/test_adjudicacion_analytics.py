from __future__ import annotations

from datetime import date, datetime

from app.application.use_cases.adjudicacion_analytics import (
    AdjudicacionAnalyticsUseCase,
    PersistAnalyticsByDateInput,
)
from app.domain.entities.adjudicacion_analytics import (
    AdjudicacionAnalyticsSnapshotRecord,
)
from app.integrations.chilecompra.models import (
    AdjudicacionAnalyticInsight,
    AdjudicacionesAnalyticsResult,
    AdjudicacionesAnalyticsSummary,
)


class SpyAdjudicacionAnalyticsRepository:
    def __init__(self) -> None:
        self.saved: list[AdjudicacionAnalyticsSnapshotRecord] = []

    def add_many(
        self, entities: list[AdjudicacionAnalyticsSnapshotRecord]
    ) -> list[AdjudicacionAnalyticsSnapshotRecord]:
        self.saved.extend(entities)
        return entities

    def list_by_external_id(self, external_id: str, limit: int = 50):
        return []

    def get_latest(self, external_id: str):
        return None

    def list_by_snapshot_date(self, snapshot_date: date):
        return []

    def list_by_date_range(self, start_date: date, end_date: date):
        return []


class FakeAdjudicacionesClient:
    def __init__(self, result: AdjudicacionesAnalyticsResult) -> None:
        self._result = result

    async def analisis_oportunidad_por_fecha(self, fecha, config=None):
        return self._result


class FakeChileCompraClient:
    def __init__(self, result: AdjudicacionesAnalyticsResult) -> None:
        self.adjudicaciones = FakeAdjudicacionesClient(result)


def test_persist_by_date_marks_fallback_source_in_source_filters() -> None:
    repository = SpyAdjudicacionAnalyticsRepository()
    result = AdjudicacionesAnalyticsResult(
        summary=AdjudicacionesAnalyticsSummary(
            total_items=1,
            scored_items=1,
            outlier_items=0,
            avg_opportunity_score=55.0,
            median_award_ratio=None,
            risk_distribution={"low": 0, "medium": 1, "high": 0},
        ),
        items=[
            AdjudicacionAnalyticInsight(
                external_id="1000-01-LR26",
                opportunity_score=55.0,
                risk_level="medium",
                is_outlier=False,
                reasons=["fallback_source_data"],
                award_ratio=None,
                awarded_amount=None,
                quality_flags=["fallback_payload_from_licitaciones"],
            )
        ],
    )
    use_case = AdjudicacionAnalyticsUseCase(
        repository=repository,
        chilecompra_client=FakeChileCompraClient(result),
    )

    import asyncio

    asyncio.run(use_case.persist_by_date(PersistAnalyticsByDateInput(fecha="06082026")))

    assert len(repository.saved) == 1
    assert repository.saved[0].source_filters == {
        "fecha": "06082026",
        "source_resource": "licitaciones.json",
        "degraded_source": "true",
    }

    assert repository.saved[0].quality_flags == ["fallback_payload_from_licitaciones"]
    assert repository.saved[0].scored_at <= datetime.now(
        repository.saved[0].scored_at.tzinfo
    )
