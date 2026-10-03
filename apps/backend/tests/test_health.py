from datetime import date, datetime

from app.api.deps.container import (
    get_adjudicacion_analytics_use_case,
    get_document_storage_use_case,
)
from app.api.deps.settings import get_settings
from app.application.use_cases.adjudicacion_analytics import (
    AdjudicacionDashboardRecord,
    AdjudicacionesDashboardSummary,
    AdjudicacionesTimeseriesPoint,
    PersistAnalyticsByDateInput,
    PersistAnalyticsByQueryInput,
)
from app.application.use_cases.document_storage import DocumentStorageUseCase
from app.domain.entities.adjudicacion_analytics import (
    AdjudicacionAnalyticsSnapshotRecord,
)
from app.domain.entities.document import DocumentMetadataRecord
from app.integrations.chilecompra.exceptions import (
    ChileCompraNotFoundError,
    ChileCompraValidationError,
)
from app.integrations.chilecompra.models import (
    AdjudicacionAnalyticInsight,
    AdjudicacionesAnalyticsResult,
    AdjudicacionesAnalyticsSummary,
)
from app.db.dependencies import get_current_user
from app.main import app
from fastapi.testclient import TestClient
from types import SimpleNamespace


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def upload(
        self, bucket: str, object_name: str, data: bytes, content_type: str
    ) -> str:
        self.objects[(bucket, object_name)] = data
        return f"s3://{bucket}/{object_name}"

    def download(self, bucket: str, object_name: str) -> bytes:
        return self.objects[(bucket, object_name)]

    def delete(self, bucket: str, object_name: str) -> None:
        self.objects.pop((bucket, object_name), None)

    def ensure_bucket(self, bucket: str) -> None:
        return None

    def list_buckets(self) -> list[str]:
        return []

    def presign_download(
        self, bucket: str, object_name: str, expires_in_seconds: int
    ) -> str:
        return (
            f"https://signed.local/{bucket}/{object_name}?expires={expires_in_seconds}"
        )


class InMemoryDocumentMetadataRepository:
    def __init__(self) -> None:
        self.records: dict[str, DocumentMetadataRecord] = {}

    def add(self, entity: DocumentMetadataRecord) -> DocumentMetadataRecord:
        self.records[entity.object_name] = entity
        return entity

    def get_by_object_name(self, object_name: str) -> DocumentMetadataRecord | None:
        return self.records.get(object_name)

    def list(self) -> list[DocumentMetadataRecord]:
        return list(self.records.values())

    def remove(self, object_name: str) -> None:
        self.records.pop(object_name, None)


class InMemoryAdjudicacionAnalyticsUseCase:
    def __init__(self) -> None:
        self.items: list[AdjudicacionAnalyticsSnapshotRecord] = []
        self.persist_by_date_error: Exception | None = None
        self.persist_by_query_error: Exception | None = None

    async def persist_by_date(
        self, payload: PersistAnalyticsByDateInput
    ) -> AdjudicacionesAnalyticsResult:
        if self.persist_by_date_error is not None:
            raise self.persist_by_date_error

        snapshot = AdjudicacionAnalyticsSnapshotRecord(
            id=1,
            external_id="1000-01-LR26",
            snapshot_date=date(2026, 8, 6),
            scored_at=datetime(2026, 8, 6, 12, 0, 0),
            opportunity_score=72.5,
            risk_level="low",
            is_outlier=False,
            reasons=["fallback_source_data"],
            award_ratio=0.78,
            awarded_amount=1250000.0,
            quality_flags=["fallback_payload_from_licitaciones"],
            source_filters={
                "fecha": "06082026",
                "source_resource": "licitaciones.json",
                "degraded_source": "true",
            },
        )
        self.items.append(snapshot)
        return AdjudicacionesAnalyticsResult(
            summary=AdjudicacionesAnalyticsSummary(
                total_items=1,
                scored_items=1,
                outlier_items=0,
                avg_opportunity_score=72.5,
                median_award_ratio=0.78,
                risk_distribution={"low": 1, "medium": 0, "high": 0},
            ),
            items=[
                AdjudicacionAnalyticInsight(
                    external_id="1000-01-LR26",
                    opportunity_score=72.5,
                    risk_level="low",
                    is_outlier=False,
                    reasons=["fallback_source_data"],
                    award_ratio=0.78,
                    awarded_amount=1250000.0,
                    quality_flags=["fallback_payload_from_licitaciones"],
                )
            ],
        )

    async def persist_by_query(
        self, payload: PersistAnalyticsByQueryInput
    ) -> AdjudicacionesAnalyticsResult:
        if self.persist_by_query_error is not None:
            raise self.persist_by_query_error

        snapshot = AdjudicacionAnalyticsSnapshotRecord(
            id=2,
            external_id="1000-02-LR26",
            snapshot_date=payload.snapshot_date,
            scored_at=datetime(2026, 8, 6, 13, 0, 0),
            opportunity_score=48.0,
            risk_level="medium",
            is_outlier=True,
            reasons=["high_award_ratio"],
            award_ratio=1.9,
            awarded_amount=9000000.0,
            quality_flags=[],
            source_filters={"estado": "ADJUDICADA"},
        )
        self.items.append(snapshot)
        return AdjudicacionesAnalyticsResult(
            summary=AdjudicacionesAnalyticsSummary(
                total_items=1,
                scored_items=1,
                outlier_items=1,
                avg_opportunity_score=48.0,
                median_award_ratio=1.9,
                risk_distribution={"low": 0, "medium": 1, "high": 0},
            ),
            items=[
                AdjudicacionAnalyticInsight(
                    external_id="1000-02-LR26",
                    opportunity_score=48.0,
                    risk_level="medium",
                    is_outlier=True,
                    reasons=["high_award_ratio"],
                    award_ratio=1.9,
                    awarded_amount=9000000.0,
                    quality_flags=[],
                )
            ],
        )

    def history(
        self, external_id: str, limit: int = 50
    ) -> list[AdjudicacionAnalyticsSnapshotRecord]:
        records = [item for item in self.items if item.external_id == external_id]
        return records[:limit]

    def latest(self, external_id: str) -> AdjudicacionAnalyticsSnapshotRecord | None:
        for item in reversed(self.items):
            if item.external_id == external_id:
                return item
        return None

    def timeseries(
        self,
        start_date: date,
        end_date: date,
    ) -> list[AdjudicacionesTimeseriesPoint]:
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        grouped: dict[date, list[AdjudicacionAnalyticsSnapshotRecord]] = {}
        for item in self.items:
            if start_date <= item.snapshot_date <= end_date:
                grouped.setdefault(item.snapshot_date, []).append(item)

        points: list[AdjudicacionesTimeseriesPoint] = []
        for snapshot_date in sorted(grouped.keys()):
            rows = grouped[snapshot_date]
            risk_distribution = {"low": 0, "medium": 0, "high": 0}
            for row in rows:
                risk_distribution[row.risk_level] = (
                    risk_distribution.get(row.risk_level, 0) + 1
                )

            avg_score = round(sum(row.opportunity_score for row in rows) / len(rows), 2)
            degraded_items = sum(
                1
                for row in rows
                if row.quality_flags
                and "fallback_payload_from_licitaciones" in row.quality_flags
            )
            points.append(
                AdjudicacionesTimeseriesPoint(
                    snapshot_date=snapshot_date,
                    total_items=len(rows),
                    outlier_items=sum(1 for row in rows if row.is_outlier),
                    degraded_items=degraded_items,
                    degraded_ratio=round(degraded_items / len(rows), 4),
                    avg_opportunity_score=avg_score,
                    risk_distribution=risk_distribution,
                )
            )
        return points

    def dashboard_summary(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
        risk_level: str | None = None,
        only_degraded: bool = False,
        only_outliers: bool = False,
        breakdown_limit: int | None = None,
        breakdown_sort_by: str = "total_items",
        breakdown_desc: bool = True,
        min_total_items: int | None = None,
        min_degraded_ratio: float | None = None,
        breakdown_page: int = 1,
        breakdown_page_size: int | None = None,
    ) -> AdjudicacionesDashboardSummary:
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")
        if breakdown_limit is not None and breakdown_limit < 1:
            raise ValueError("breakdown_limit must be greater than or equal to 1")
        if min_total_items is not None and min_total_items < 1:
            raise ValueError("min_total_items must be greater than or equal to 1")
        if min_degraded_ratio is not None and not 0 <= min_degraded_ratio <= 1:
            raise ValueError("min_degraded_ratio must be between 0 and 1")
        if breakdown_page < 1:
            raise ValueError("breakdown_page must be greater than or equal to 1")
        if breakdown_page_size is not None and breakdown_page_size < 1:
            raise ValueError("breakdown_page_size must be greater than or equal to 1")
        normalized_risk = risk_level.strip().lower() if risk_level else None
        if normalized_risk and normalized_risk not in {"low", "medium", "high"}:
            raise ValueError("risk_level must be one of: low, medium, high")
        normalized_sort = breakdown_sort_by.strip().lower()
        if normalized_sort not in {
            "total_items",
            "outlier_ratio",
            "degraded_ratio",
            "avg_opportunity_score",
        }:
            raise ValueError(
                "breakdown_sort_by must be one of: total_items, outlier_ratio, degraded_ratio, avg_opportunity_score"
            )

        rows = [
            item for item in self.items if start_date <= item.snapshot_date <= end_date
        ]
        if normalized_risk:
            rows = [item for item in rows if item.risk_level == normalized_risk]
        if only_degraded:
            rows = [
                item
                for item in rows
                if item.quality_flags
                and "fallback_payload_from_licitaciones" in item.quality_flags
            ]
        if only_outliers:
            rows = [item for item in rows if item.is_outlier]

        risk_distribution = {"low": 0, "medium": 0, "high": 0}
        for row in rows:
            risk_distribution[row.risk_level] = (
                risk_distribution.get(row.risk_level, 0) + 1
            )

        degraded_items = sum(
            1
            for row in rows
            if row.quality_flags
            and "fallback_payload_from_licitaciones" in row.quality_flags
        )
        outlier_items = sum(1 for row in rows if row.is_outlier)
        avg_score = (
            round(sum(row.opportunity_score for row in rows) / len(rows), 2)
            if rows
            else None
        )

        def to_record(
            row: AdjudicacionAnalyticsSnapshotRecord,
        ) -> AdjudicacionDashboardRecord:
            return AdjudicacionDashboardRecord(
                external_id=row.external_id,
                snapshot_date=row.snapshot_date,
                opportunity_score=row.opportunity_score,
                risk_level=row.risk_level,
                is_outlier=row.is_outlier,
                is_degraded_source=bool(
                    row.quality_flags
                    and "fallback_payload_from_licitaciones" in row.quality_flags
                ),
                awarded_amount=row.awarded_amount,
                award_ratio=row.award_ratio,
                reasons=row.reasons,
                quality_flags=row.quality_flags or [],
            )

        def build_breakdown(selector):
            grouped: dict[str, list[AdjudicacionAnalyticsSnapshotRecord]] = {}
            for row in rows:
                grouped.setdefault(str(selector(row)), []).append(row)

            breakdown = []
            for segment, items in sorted(
                grouped.items(), key=lambda pair: len(pair[1]), reverse=True
            ):
                total = len(items)
                outliers = sum(1 for item in items if item.is_outlier)
                degraded = sum(
                    1
                    for item in items
                    if item.quality_flags
                    and "fallback_payload_from_licitaciones" in item.quality_flags
                )
                avg = round(sum(item.opportunity_score for item in items) / total, 2)
                risks = {"low": 0, "medium": 0, "high": 0}
                for item in items:
                    risks[item.risk_level] = risks.get(item.risk_level, 0) + 1
                breakdown.append(
                    {
                        "segment": segment,
                        "total_items": total,
                        "outlier_items": outliers,
                        "degraded_items": degraded,
                        "outlier_ratio": round(outliers / total, 4),
                        "degraded_ratio": round(degraded / total, 4),
                        "avg_opportunity_score": avg,
                        "risk_distribution": risks,
                    }
                )

            def metric(item):
                if normalized_sort == "total_items":
                    return float(item["total_items"])
                if normalized_sort == "outlier_ratio":
                    return float(item["outlier_ratio"])
                if normalized_sort == "degraded_ratio":
                    return float(item["degraded_ratio"])
                return float(item["avg_opportunity_score"] or 0.0)

            if breakdown_desc:
                breakdown.sort(
                    key=lambda item: (
                        -metric(item),
                        -float(item["total_items"]),
                        item["segment"],
                    )
                )
            else:
                breakdown.sort(
                    key=lambda item: (
                        metric(item),
                        float(item["total_items"]),
                        item["segment"],
                    )
                )
            if min_total_items is not None:
                breakdown = [
                    item for item in breakdown if item["total_items"] >= min_total_items
                ]
            if min_degraded_ratio is not None:
                breakdown = [
                    item
                    for item in breakdown
                    if item["degraded_ratio"] >= min_degraded_ratio
                ]
            if breakdown_limit is not None:
                breakdown = breakdown[:breakdown_limit]
            return breakdown

        def paginate_breakdown(items):
            total_items = len(items)
            page_size = (
                breakdown_page_size
                if breakdown_page_size is not None
                else (total_items if total_items > 0 else 1)
            )
            total_pages = (
                (total_items + page_size - 1) // page_size if total_items > 0 else 1
            )
            current_page = (
                breakdown_page if breakdown_page <= total_pages else total_pages
            )
            start = (current_page - 1) * page_size
            end = start + page_size
            paged_items = items[start:end]
            return paged_items, {
                "page": current_page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": current_page < total_pages,
                "has_prev": current_page > 1,
                "next_page": current_page + 1 if current_page < total_pages else None,
                "prev_page": current_page - 1 if current_page > 1 else None,
                "sort_by": normalized_sort,
                "sort_desc": breakdown_desc,
            }

        source_breakdown, source_breakdown_pagination = paginate_breakdown(
            build_breakdown(
                lambda row: (
                    (row.source_filters or {}).get("source_resource") or "unknown"
                )
            )
        )
        organization_breakdown, organization_breakdown_pagination = paginate_breakdown(
            build_breakdown(lambda row: row.external_id.split("-", 1)[0])
        )

        return AdjudicacionesDashboardSummary(
            start_date=start_date,
            end_date=end_date,
            total_items=len(rows),
            unique_external_ids=len({row.external_id for row in rows}),
            outlier_items=outlier_items,
            degraded_items=degraded_items,
            outlier_ratio=round(outlier_items / len(rows), 4) if rows else 0.0,
            degraded_ratio=round(degraded_items / len(rows), 4) if rows else 0.0,
            avg_opportunity_score=avg_score,
            risk_distribution=risk_distribution,
            applied_filters={
                "limit": limit,
                "risk_level": normalized_risk or "all",
                "only_degraded": only_degraded,
                "only_outliers": only_outliers,
                "breakdown_limit": (
                    breakdown_limit if breakdown_limit is not None else "all"
                ),
                "breakdown_sort_by": normalized_sort,
                "breakdown_desc": breakdown_desc,
                "min_total_items": (
                    min_total_items if min_total_items is not None else "all"
                ),
                "min_degraded_ratio": (
                    min_degraded_ratio if min_degraded_ratio is not None else "all"
                ),
                "breakdown_page": breakdown_page,
                "breakdown_page_size": (
                    breakdown_page_size if breakdown_page_size is not None else "all"
                ),
            },
            source_breakdown=source_breakdown,
            source_breakdown_pagination=source_breakdown_pagination,
            organization_breakdown=organization_breakdown,
            organization_breakdown_pagination=organization_breakdown_pagination,
            top_risk_items=[
                to_record(row)
                for row in sorted(rows, key=lambda row: row.opportunity_score)[:limit]
            ],
            top_opportunity_items=[
                to_record(row)
                for row in sorted(rows, key=lambda row: -row.opportunity_score)[:limit]
            ],
        )


def build_test_client(
    analytics_use_case: InMemoryAdjudicacionAnalyticsUseCase | None = None,
) -> TestClient:
    app.dependency_overrides.clear()
    settings = get_settings()
    analytics_use_case = analytics_use_case or InMemoryAdjudicacionAnalyticsUseCase()
    storage_use_case = DocumentStorageUseCase(
        InMemoryObjectStorage(),
        InMemoryDocumentMetadataRepository(),
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_document_storage_use_case] = lambda: storage_use_case
    app.dependency_overrides[get_adjudicacion_analytics_use_case] = lambda: (
        analytics_use_case
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        email="test@example.com", is_active=True
    )
    return TestClient(app)


def test_health_endpoint() -> None:
    client = build_test_client()
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MercadoInsight API",
        "version": "0.1.0",
        "environment": get_settings().environment,
    }


def test_root_metadata_endpoint() -> None:
    client = build_test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "MercadoInsight API"


def test_document_upload_and_download() -> None:
    client = build_test_client()

    upload_response = client.post(
        "/api/v1/documents/sample.txt",
        files={"file": ("sample.txt", b"hello market", "text/plain")},
    )

    assert upload_response.status_code == 200
    assert upload_response.json() == {
        "bucket": "documents-private",
        "object_name": "sample.txt",
        "uri": "s3://documents-private/sample.txt",
        "is_public": False,
    }

    download_response = client.get("/api/v1/documents/sample.txt")

    assert download_response.status_code == 200
    assert download_response.content == b"hello market"


def test_public_document_download_url() -> None:
    client = build_test_client()

    upload_response = client.post(
        "/api/v1/documents/public.txt",
        data={"is_public": "true"},
        files={"file": ("public.txt", b"public market", "text/plain")},
    )

    assert upload_response.status_code == 200
    assert upload_response.json() == {
        "bucket": "documents-public",
        "object_name": "public.txt",
        "uri": "s3://documents-public/public.txt",
        "is_public": True,
    }

    download_url_response = client.get("/api/v1/documents/public.txt/download-url")

    assert download_url_response.status_code == 200
    assert download_url_response.json()["is_public"] is True
    assert download_url_response.json()["download_url"].startswith(
        "http://minio:9000/documents-public/public.txt"
    )


def test_metrics_endpoint_exposes_backend_metrics() -> None:
    client = build_test_client()

    health_response = client.get("/api/v1/health")
    assert health_response.status_code == 200

    metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    assert "market_insight_http_requests_total" in metrics_response.text
    assert "market_insight_http_request_duration_seconds" in metrics_response.text


def test_ingest_analytics_by_date_endpoint() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )

    assert response.status_code == 200
    assert response.json()["persisted_items"] == 1
    assert response.json()["outlier_items"] == 0


def test_ingest_analytics_by_query_and_fetch_history() -> None:
    client = build_test_client()

    ingest = client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["outlier_items"] == 1

    history = client.get("/api/v1/analytics/adjudicaciones/1000-02-LR26/history")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["risk_level"] == "medium"
    assert history.json()[0]["is_degraded_source"] is False
    assert history.json()[0]["source_resource"] is None

    latest = client.get("/api/v1/analytics/adjudicaciones/1000-02-LR26/latest")
    assert latest.status_code == 200
    assert latest.json()["is_outlier"] is True


def test_adjudicaciones_latest_exposes_degraded_source_flags() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )

    latest = client.get("/api/v1/analytics/adjudicaciones/1000-01-LR26/latest")

    assert latest.status_code == 200
    assert latest.json()["is_degraded_source"] is True
    assert latest.json()["source_resource"] == "licitaciones.json"


def test_adjudicaciones_timeseries_endpoint() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )
    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    response = client.get(
        "/api/v1/analytics/adjudicaciones/timeseries?start_date=2026-08-06&end_date=2026-08-06"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["snapshot_date"] == "2026-08-06"
    assert payload[0]["total_items"] == 2
    assert payload[0]["outlier_items"] == 1
    assert payload[0]["degraded_items"] == 1
    assert payload[0]["degraded_ratio"] == 0.5


def test_adjudicaciones_timeseries_endpoint_invalid_range() -> None:
    client = build_test_client()

    response = client.get(
        "/api/v1/analytics/adjudicaciones/timeseries?start_date=2026-08-07&end_date=2026-08-06"
    )

    assert response.status_code == 422


def test_adjudicaciones_dashboard_endpoint() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )
    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&limit=1"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 2
    assert payload["unique_external_ids"] == 2
    assert payload["outlier_items"] == 1
    assert payload["degraded_items"] == 1
    assert payload["degraded_ratio"] == 0.5
    assert payload["applied_filters"]["risk_level"] == "all"
    assert payload["source_breakdown"][0]["segment"] == "licitaciones.json"
    assert payload["source_breakdown_pagination"]["page"] == 1
    assert payload["source_breakdown_pagination"]["total_items"] == 2
    assert payload["organization_breakdown"][0]["segment"] == "1000"
    assert payload["organization_breakdown_pagination"]["page"] == 1
    assert payload["organization_breakdown_pagination"]["total_items"] == 1
    assert len(payload["top_risk_items"]) == 1
    assert len(payload["top_opportunity_items"]) == 1


def test_adjudicaciones_dashboard_endpoint_invalid_limit() -> None:
    client = build_test_client()

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&limit=0"
    )

    assert response.status_code == 422


def test_adjudicaciones_dashboard_endpoint_filters() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )
    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    filtered = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&risk_level=medium&only_outliers=true&only_degraded=false"
    )

    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total_items"] == 1
    assert payload["risk_distribution"] == {"low": 0, "medium": 1, "high": 0}
    assert payload["applied_filters"]["risk_level"] == "medium"
    assert payload["applied_filters"]["only_outliers"] is True
    assert payload["applied_filters"]["only_degraded"] is False


def test_adjudicaciones_dashboard_endpoint_invalid_risk_level() -> None:
    client = build_test_client()

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&risk_level=critical"
    )

    assert response.status_code == 422


def test_adjudicaciones_dashboard_endpoint_breakdown_controls() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )
    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&breakdown_limit=1&breakdown_sort_by=degraded_ratio&breakdown_desc=false&min_total_items=1&min_degraded_ratio=0.0"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied_filters"]["breakdown_limit"] == 1
    assert payload["applied_filters"]["breakdown_sort_by"] == "degraded_ratio"
    assert payload["applied_filters"]["breakdown_desc"] is False
    assert payload["applied_filters"]["min_total_items"] == 1
    assert payload["applied_filters"]["min_degraded_ratio"] == 0.0
    assert len(payload["source_breakdown"]) == 1
    assert payload["source_breakdown"][0]["segment"] == "unknown"


def test_adjudicaciones_dashboard_endpoint_invalid_breakdown_sort_by() -> None:
    client = build_test_client()

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&breakdown_sort_by=risk_score"
    )

    assert response.status_code == 422


def test_adjudicaciones_dashboard_endpoint_threshold_filters() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )
    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&min_total_items=2&min_degraded_ratio=1"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_breakdown"] == []
    assert payload["organization_breakdown"] == []


def test_adjudicaciones_dashboard_endpoint_invalid_min_degraded_ratio() -> None:
    client = build_test_client()

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&min_degraded_ratio=1.1"
    )

    assert response.status_code == 422


def test_adjudicaciones_dashboard_endpoint_breakdown_pagination() -> None:
    client = build_test_client()

    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )
    client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&breakdown_page=2&breakdown_page_size=1"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_breakdown_pagination"]["page"] == 2
    assert payload["source_breakdown_pagination"]["page_size"] == 1
    assert payload["source_breakdown_pagination"]["total_items"] == 2
    assert payload["source_breakdown_pagination"]["total_pages"] == 2
    assert payload["source_breakdown_pagination"]["has_prev"] is True
    assert payload["source_breakdown_pagination"]["has_next"] is False
    assert payload["source_breakdown"][0]["segment"] == "unknown"


def test_adjudicaciones_dashboard_endpoint_invalid_breakdown_page_size() -> None:
    client = build_test_client()

    response = client.get(
        "/api/v1/analytics/adjudicaciones/dashboard?start_date=2026-08-06&end_date=2026-08-06&breakdown_page_size=0"
    )

    assert response.status_code == 422


def test_ingest_by_date_translates_chilecompra_not_found() -> None:
    analytics_use_case = InMemoryAdjudicacionAnalyticsUseCase()
    analytics_use_case.persist_by_date_error = ChileCompraNotFoundError(
        "ChileCompra resource not found"
    )
    client = build_test_client(analytics_use_case=analytics_use_case)

    response = client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-date",
        json={"fecha": "06082026"},
    )

    assert response.status_code == 502
    assert response.json()["error"]["message"] == "ChileCompra resource not found"


def test_ingest_by_query_translates_chilecompra_validation_error() -> None:
    analytics_use_case = InMemoryAdjudicacionAnalyticsUseCase()
    analytics_use_case.persist_by_query_error = ChileCompraValidationError(
        "Parametros de busqueda avanzada invalidos"
    )
    client = build_test_client(analytics_use_case=analytics_use_case)

    response = client.post(
        "/api/v1/analytics/adjudicaciones/ingest-by-query",
        json={
            "query": {"estado": "ADJUDICADA"},
            "snapshot_date": "2026-08-06",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Parametros de busqueda avanzada invalidos"
