from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from app.domain.entities.adjudicacion_analytics import (
    AdjudicacionAnalyticsSnapshotRecord,
)
from app.domain.ports.adjudicacion_analytics_repository import (
    AdjudicacionAnalyticsRepository,
)
from app.integrations.chilecompra.models import (
    AdjudicacionAnalyticInsight,
    AdjudicacionesAnalyticsResult,
    AdjudicacionesQuery,
    AdjudicacionesScoringConfig,
)
from app.integrations.chilecompra.sdk import ChileCompraClient

_FALLBACK_SOURCE_FLAG = "fallback_payload_from_licitaciones"
_FALLBACK_SOURCE_RESOURCE = "licitaciones.json"
BreakdownSortBy = Literal[
    "total_items", "outlier_ratio", "degraded_ratio", "avg_opportunity_score"
]
_BREAKDOWN_SORT_FIELDS = {
    "total_items",
    "outlier_ratio",
    "degraded_ratio",
    "avg_opportunity_score",
}


@dataclass(slots=True)
class PersistAnalyticsByDateInput:
    fecha: str | date | datetime
    config: AdjudicacionesScoringConfig | None = None


@dataclass(slots=True)
class PersistAnalyticsByQueryInput:
    query: AdjudicacionesQuery | dict
    snapshot_date: date
    config: AdjudicacionesScoringConfig | None = None


@dataclass(slots=True)
class AdjudicacionesTimeseriesPoint:
    snapshot_date: date
    total_items: int
    outlier_items: int
    degraded_items: int
    degraded_ratio: float
    avg_opportunity_score: float | None
    risk_distribution: dict[str, int]


@dataclass(slots=True)
class AdjudicacionDashboardRecord:
    external_id: str
    snapshot_date: date
    opportunity_score: float
    risk_level: str
    is_outlier: bool
    is_degraded_source: bool
    awarded_amount: float | None
    award_ratio: float | None
    reasons: list[str]
    quality_flags: list[str]


@dataclass(slots=True)
class AdjudicacionesDashboardSummary:
    start_date: date
    end_date: date
    total_items: int
    unique_external_ids: int
    outlier_items: int
    degraded_items: int
    outlier_ratio: float
    degraded_ratio: float
    avg_opportunity_score: float | None
    risk_distribution: dict[str, int]
    applied_filters: dict[str, str | bool | int | float]
    source_breakdown: list["AdjudicacionesDashboardBreakdown"]
    source_breakdown_pagination: "AdjudicacionesDashboardBreakdownPagination"
    organization_breakdown: list["AdjudicacionesDashboardBreakdown"]
    organization_breakdown_pagination: "AdjudicacionesDashboardBreakdownPagination"
    top_risk_items: list[AdjudicacionDashboardRecord]
    top_opportunity_items: list[AdjudicacionDashboardRecord]


@dataclass(slots=True)
class AdjudicacionesDashboardBreakdown:
    segment: str
    total_items: int
    outlier_items: int
    degraded_items: int
    outlier_ratio: float
    degraded_ratio: float
    avg_opportunity_score: float | None
    risk_distribution: dict[str, int]


@dataclass(slots=True)
class AdjudicacionesDashboardBreakdownPagination:
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: int | None
    prev_page: int | None
    sort_by: BreakdownSortBy
    sort_desc: bool


class AdjudicacionAnalyticsUseCase:
    """Persist adjudicaciones analytics snapshots and expose historical queries."""

    def __init__(
        self,
        repository: AdjudicacionAnalyticsRepository,
        chilecompra_client: ChileCompraClient,
    ) -> None:
        self._repository = repository
        self._client = chilecompra_client

    async def persist_by_date(
        self, payload: PersistAnalyticsByDateInput
    ) -> AdjudicacionesAnalyticsResult:
        analytics = await self._client.adjudicaciones.analisis_oportunidad_por_fecha(
            payload.fecha,
            config=payload.config,
        )
        snapshot_date = _normalize_snapshot_date(payload.fecha)
        source_filters = {"fecha": snapshot_date.strftime("%d%m%Y")}
        self._persist_result(analytics, snapshot_date, source_filters)
        return analytics

    async def persist_by_query(
        self, payload: PersistAnalyticsByQueryInput
    ) -> AdjudicacionesAnalyticsResult:
        analytics = (
            await self._client.adjudicaciones.analisis_oportunidad_busqueda_avanzada(
                payload.query,
                config=payload.config,
            )
        )
        source_filters = _query_filters(payload.query)
        self._persist_result(analytics, payload.snapshot_date, source_filters)
        return analytics

    def history(
        self, external_id: str, limit: int = 50
    ) -> list[AdjudicacionAnalyticsSnapshotRecord]:
        return list(
            self._repository.list_by_external_id(external_id=external_id, limit=limit)
        )

    def latest(self, external_id: str) -> AdjudicacionAnalyticsSnapshotRecord | None:
        return self._repository.get_latest(external_id)

    def timeseries(
        self,
        start_date: date,
        end_date: date,
    ) -> list[AdjudicacionesTimeseriesPoint]:
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        rows = list(self._repository.list_by_date_range(start_date, end_date))
        grouped: dict[date, list[AdjudicacionAnalyticsSnapshotRecord]] = {}
        for row in rows:
            grouped.setdefault(row.snapshot_date, []).append(row)

        series: list[AdjudicacionesTimeseriesPoint] = []
        for snapshot_date in sorted(grouped.keys()):
            points = grouped[snapshot_date]
            risk_distribution = {"low": 0, "medium": 0, "high": 0}
            for point in points:
                risk_distribution[point.risk_level] = (
                    risk_distribution.get(point.risk_level, 0) + 1
                )

            degraded_items = sum(
                1
                for point in points
                if point.quality_flags and _FALLBACK_SOURCE_FLAG in point.quality_flags
            )

            avg_score = (
                round(sum(point.opportunity_score for point in points) / len(points), 2)
                if points
                else None
            )
            series.append(
                AdjudicacionesTimeseriesPoint(
                    snapshot_date=snapshot_date,
                    total_items=len(points),
                    outlier_items=sum(1 for point in points if point.is_outlier),
                    degraded_items=degraded_items,
                    degraded_ratio=round(degraded_items / len(points), 4),
                    avg_opportunity_score=avg_score,
                    risk_distribution=risk_distribution,
                )
            )
        return series

    def dashboard_summary(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
        risk_level: str | None = None,
        only_degraded: bool = False,
        only_outliers: bool = False,
        breakdown_limit: int | None = None,
        breakdown_sort_by: BreakdownSortBy = "total_items",
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
        normalized_risk_level = _normalize_risk_level(risk_level)
        normalized_breakdown_sort = _normalize_breakdown_sort_by(breakdown_sort_by)

        rows = list(self._repository.list_by_date_range(start_date, end_date))
        rows = [
            row
            for row in rows
            if _matches_dashboard_filters(
                row,
                risk_level=normalized_risk_level,
                only_degraded=only_degraded,
                only_outliers=only_outliers,
            )
        ]
        total_items = len(rows)
        risk_distribution = {"low": 0, "medium": 0, "high": 0}
        for row in rows:
            risk_distribution[row.risk_level] = (
                risk_distribution.get(row.risk_level, 0) + 1
            )

        degraded_items = sum(
            1
            for row in rows
            if row.quality_flags and _FALLBACK_SOURCE_FLAG in row.quality_flags
        )
        outlier_items = sum(1 for row in rows if row.is_outlier)
        avg_score = (
            round(sum(row.opportunity_score for row in rows) / total_items, 2)
            if total_items
            else None
        )

        top_risk_rows = sorted(
            rows,
            key=lambda row: (
                row.opportunity_score,
                0 if row.is_outlier else 1,
                row.snapshot_date,
            ),
        )[:limit]
        top_opportunity_rows = sorted(
            rows,
            key=lambda row: (
                -row.opportunity_score,
                0 if row.is_outlier else 1,
                row.snapshot_date,
            ),
        )[:limit]

        source_breakdown = _build_breakdown(
            rows,
            key_selector=lambda row: _source_resource(row) or "unknown",
            sort_by=normalized_breakdown_sort,
            descending=breakdown_desc,
            limit=breakdown_limit,
            min_total_items=min_total_items,
            min_degraded_ratio=min_degraded_ratio,
        )
        paged_source_breakdown, source_breakdown_pagination = _paginate_breakdown(
            source_breakdown,
            page=breakdown_page,
            page_size=breakdown_page_size,
            sort_by=normalized_breakdown_sort,
            descending=breakdown_desc,
        )

        organization_breakdown = _build_breakdown(
            rows,
            key_selector=_organization_hint,
            sort_by=normalized_breakdown_sort,
            descending=breakdown_desc,
            limit=breakdown_limit,
            min_total_items=min_total_items,
            min_degraded_ratio=min_degraded_ratio,
        )
        paged_organization_breakdown, organization_breakdown_pagination = (
            _paginate_breakdown(
                organization_breakdown,
                page=breakdown_page,
                page_size=breakdown_page_size,
                sort_by=normalized_breakdown_sort,
                descending=breakdown_desc,
            )
        )

        return AdjudicacionesDashboardSummary(
            start_date=start_date,
            end_date=end_date,
            total_items=total_items,
            unique_external_ids=len({row.external_id for row in rows}),
            outlier_items=outlier_items,
            degraded_items=degraded_items,
            outlier_ratio=round(outlier_items / total_items, 4) if total_items else 0.0,
            degraded_ratio=round(degraded_items / total_items, 4)
            if total_items
            else 0.0,
            avg_opportunity_score=avg_score,
            risk_distribution=risk_distribution,
            applied_filters={
                "limit": limit,
                "risk_level": normalized_risk_level or "all",
                "only_degraded": only_degraded,
                "only_outliers": only_outliers,
                "breakdown_limit": (
                    breakdown_limit if breakdown_limit is not None else "all"
                ),
                "breakdown_sort_by": normalized_breakdown_sort,
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
            source_breakdown=paged_source_breakdown,
            source_breakdown_pagination=source_breakdown_pagination,
            organization_breakdown=paged_organization_breakdown,
            organization_breakdown_pagination=organization_breakdown_pagination,
            top_risk_items=[_to_dashboard_record(row) for row in top_risk_rows],
            top_opportunity_items=[
                _to_dashboard_record(row) for row in top_opportunity_rows
            ],
        )

    def _persist_result(
        self,
        result: AdjudicacionesAnalyticsResult,
        snapshot_date: date,
        source_filters: dict[str, str],
    ) -> None:
        now = datetime.now(ZoneInfo("UTC"))
        source_filters = _enrich_source_filters(source_filters, result)
        entities = [
            self._to_snapshot_entity(
                item=item,
                snapshot_date=snapshot_date,
                scored_at=now,
                source_filters=source_filters,
            )
            for item in result.items
        ]
        if entities:
            self._repository.add_many(entities)

    @staticmethod
    def _to_snapshot_entity(
        item: AdjudicacionAnalyticInsight,
        snapshot_date: date,
        scored_at: datetime,
        source_filters: dict[str, str],
    ) -> AdjudicacionAnalyticsSnapshotRecord:
        return AdjudicacionAnalyticsSnapshotRecord(
            id=None,
            external_id=item.external_id,
            snapshot_date=snapshot_date,
            scored_at=scored_at,
            opportunity_score=item.opportunity_score,
            risk_level=item.risk_level,
            is_outlier=item.is_outlier,
            reasons=item.reasons,
            award_ratio=item.award_ratio,
            awarded_amount=item.awarded_amount,
            quality_flags=item.quality_flags,
            source_filters=source_filters,
        )


def _normalize_snapshot_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = value.strip()
    for fmt in ("%d%m%Y", "%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("Invalid snapshot date format")


def _enrich_source_filters(
    source_filters: dict[str, str],
    result: AdjudicacionesAnalyticsResult,
) -> dict[str, str]:
    if any(_FALLBACK_SOURCE_FLAG in item.quality_flags for item in result.items):
        return {
            **source_filters,
            "source_resource": _FALLBACK_SOURCE_RESOURCE,
            "degraded_source": "true",
        }
    return source_filters


def _query_filters(query: AdjudicacionesQuery | dict) -> dict[str, str]:
    if isinstance(query, dict):
        return {
            str(key): str(value) for key, value in query.items() if value is not None
        }
    data = query.model_dump(exclude_none=True)
    return {str(key): str(value) for key, value in data.items()}


def _to_dashboard_record(
    row: AdjudicacionAnalyticsSnapshotRecord,
) -> AdjudicacionDashboardRecord:
    quality_flags = row.quality_flags or []
    return AdjudicacionDashboardRecord(
        external_id=row.external_id,
        snapshot_date=row.snapshot_date,
        opportunity_score=row.opportunity_score,
        risk_level=row.risk_level,
        is_outlier=row.is_outlier,
        is_degraded_source=_FALLBACK_SOURCE_FLAG in quality_flags,
        awarded_amount=row.awarded_amount,
        award_ratio=row.award_ratio,
        reasons=row.reasons,
        quality_flags=quality_flags,
    )


def _normalize_risk_level(risk_level: str | None) -> str | None:
    if risk_level is None:
        return None
    normalized = risk_level.strip().lower()
    if normalized not in {"low", "medium", "high"}:
        raise ValueError("risk_level must be one of: low, medium, high")
    return normalized


def _normalize_breakdown_sort_by(value: BreakdownSortBy | str) -> BreakdownSortBy:
    normalized = value.strip().lower()
    if normalized not in _BREAKDOWN_SORT_FIELDS:
        raise ValueError(
            "breakdown_sort_by must be one of: total_items, outlier_ratio, degraded_ratio, avg_opportunity_score"
        )
    return normalized  # type: ignore[return-value]


def _is_degraded(row: AdjudicacionAnalyticsSnapshotRecord) -> bool:
    quality_flags = row.quality_flags or []
    return _FALLBACK_SOURCE_FLAG in quality_flags


def _source_resource(row: AdjudicacionAnalyticsSnapshotRecord) -> str | None:
    return (row.source_filters or {}).get("source_resource")


def _organization_hint(row: AdjudicacionAnalyticsSnapshotRecord) -> str:
    head = row.external_id.split("-", 1)[0].strip()
    return head if head else "unknown"


def _matches_dashboard_filters(
    row: AdjudicacionAnalyticsSnapshotRecord,
    *,
    risk_level: str | None,
    only_degraded: bool,
    only_outliers: bool,
) -> bool:
    if risk_level is not None and row.risk_level != risk_level:
        return False
    if only_degraded and not _is_degraded(row):
        return False
    if only_outliers and not row.is_outlier:
        return False
    return True


def _build_breakdown(
    rows: list[AdjudicacionAnalyticsSnapshotRecord],
    *,
    key_selector,
    sort_by: BreakdownSortBy,
    descending: bool,
    limit: int | None,
    min_total_items: int | None,
    min_degraded_ratio: float | None,
) -> list[AdjudicacionesDashboardBreakdown]:
    grouped: dict[str, list[AdjudicacionAnalyticsSnapshotRecord]] = {}
    for row in rows:
        grouped.setdefault(str(key_selector(row)), []).append(row)

    breakdown: list[AdjudicacionesDashboardBreakdown] = []
    for segment, items in sorted(
        grouped.items(), key=lambda pair: len(pair[1]), reverse=True
    ):
        total_items = len(items)
        outlier_items = sum(1 for item in items if item.is_outlier)
        degraded_items = sum(1 for item in items if _is_degraded(item))
        avg_score = round(
            sum(item.opportunity_score for item in items) / total_items, 2
        )
        risk_distribution = {"low": 0, "medium": 0, "high": 0}
        for item in items:
            risk_distribution[item.risk_level] = (
                risk_distribution.get(item.risk_level, 0) + 1
            )

        breakdown.append(
            AdjudicacionesDashboardBreakdown(
                segment=segment,
                total_items=total_items,
                outlier_items=outlier_items,
                degraded_items=degraded_items,
                outlier_ratio=round(outlier_items / total_items, 4),
                degraded_ratio=round(degraded_items / total_items, 4),
                avg_opportunity_score=avg_score,
                risk_distribution=risk_distribution,
            )
        )

    if min_total_items is not None:
        breakdown = [item for item in breakdown if item.total_items >= min_total_items]
    if min_degraded_ratio is not None:
        breakdown = [
            item for item in breakdown if item.degraded_ratio >= min_degraded_ratio
        ]

    if descending:
        breakdown.sort(
            key=lambda item: (
                -_breakdown_metric(item, sort_by),
                -item.total_items,
                item.segment,
            )
        )
    else:
        breakdown.sort(
            key=lambda item: (
                _breakdown_metric(item, sort_by),
                item.total_items,
                item.segment,
            )
        )
    if limit is not None:
        return breakdown[:limit]
    return breakdown


def _breakdown_metric(item: AdjudicacionesDashboardBreakdown, sort_by: str) -> float:
    if sort_by == "total_items":
        return float(item.total_items)
    if sort_by == "outlier_ratio":
        return item.outlier_ratio
    if sort_by == "degraded_ratio":
        return item.degraded_ratio
    return item.avg_opportunity_score or 0.0


def _paginate_breakdown(
    items: list[AdjudicacionesDashboardBreakdown],
    *,
    page: int,
    page_size: int | None,
    sort_by: BreakdownSortBy,
    descending: bool,
) -> tuple[
    list[AdjudicacionesDashboardBreakdown],
    AdjudicacionesDashboardBreakdownPagination,
]:
    total_items = len(items)
    if page_size is None:
        effective_page_size = total_items if total_items > 0 else 1
    else:
        effective_page_size = page_size

    total_pages = (
        (total_items + effective_page_size - 1) // effective_page_size
        if total_items > 0
        else 1
    )
    current_page = page if page <= total_pages else total_pages

    start = (current_page - 1) * effective_page_size
    end = start + effective_page_size
    paged_items = items[start:end]

    has_prev = current_page > 1
    has_next = current_page < total_pages
    pagination = AdjudicacionesDashboardBreakdownPagination(
        page=current_page,
        page_size=effective_page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=current_page + 1 if has_next else None,
        prev_page=current_page - 1 if has_prev else None,
        sort_by=sort_by,
        sort_desc=descending,
    )
    return paged_items, pagination
