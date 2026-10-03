from dataclasses import asdict
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps.use_cases import (
    AdjudicacionAnalyticsUseCase,
    get_adjudicacion_analytics_use_case,
)
from app.application.use_cases.adjudicacion_analytics import (
    PersistAnalyticsByDateInput,
    PersistAnalyticsByQueryInput,
)
from app.schemas.adjudicacion_analytics import (
    AdjudicacionAnalyticsSnapshotRead,
    AdjudicacionesDashboardSummaryResponse,
    AdjudicacionesPersistenceSummaryResponse,
    AdjudicacionesTimeseriesPointResponse,
    PersistAdjudicacionesByDateRequest,
    PersistAdjudicacionesByQueryRequest,
)
from app.schemas.analytics import (
    CategorySpendingRead,
    CompetitionSummaryRead,
    DataQualityMissingKeysRead,
    DisabilityContractRead,
    MarketMonthlyRead,
    MarketObjectiveRead,
    PriceItemRead,
    SupplierPerformanceRead,
)
from app.db.dependencies import get_analytics_repository, get_segmento, get_segmento_licitacion_ids
from app.nlp.segmento import Segmento
from app.repositories.analytics import AnalyticsRepository

router = APIRouter()


@router.get(
    "/market/monthly",
    response_model=list[MarketMonthlyRead],
    summary="Monthly market indicators",
    description="Total licitaciones/adjudicaciones and awarded amount per calendar month, "
    "from the `market_monthly` data mart.",
)
async def market_monthly(
    start_month: date | None = None,
    end_month: date | None = None,
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[MarketMonthlyRead]:
    if start_month and end_month and end_month < start_month:
        raise HTTPException(status_code=422, detail="end_month must be >= start_month")
    rows = await repository.market_monthly(
        start_month=start_month,
        end_month=end_month,
        licitacion_ids=licitacion_ids,
        offset=offset,
        limit=limit,
    )
    return [MarketMonthlyRead.model_validate(row) for row in rows]


@router.get(
    "/suppliers/performance",
    response_model=list[SupplierPerformanceRead],
    summary="Supplier performance indicators",
    description="Per-supplier award history and reliability indicators, optionally "
    "filtered by name (`query`) or a minimum awarded amount.",
)
async def supplier_performance(
    query: str | None = Query(None, min_length=2, max_length=200),
    min_awarded_amount: float | None = Query(None, ge=0),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[SupplierPerformanceRead]:
    rows = await repository.supplier_performance(
        query=query,
        min_awarded_amount=min_awarded_amount,
        licitacion_ids=licitacion_ids,
        offset=offset,
        limit=limit,
    )
    return [SupplierPerformanceRead.model_validate(row) for row in rows]


@router.get(
    "/categories/spending",
    response_model=list[CategorySpendingRead],
    summary="Spending by category",
    description="Total spend per product/service category, optionally filtered by "
    "`category_code`.",
)
async def category_spending(
    category_code: str | None = Query(None, max_length=64),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[CategorySpendingRead]:
    rows = await repository.category_spending(
        category_code=category_code, licitacion_ids=licitacion_ids, offset=offset, limit=limit
    )
    return [CategorySpendingRead.model_validate(row) for row in rows]


@router.get(
    "/disability/contracts",
    response_model=list[DisabilityContractRead],
    summary="Contracts relevant to disability markets",
    description="Contracts flagged as relevant to disability-related procurement, "
    "filterable by date range, organism and supplier name.",
)
async def disability_contracts(
    start_date: date | None = None,
    end_date: date | None = None,
    organism: str | None = Query(None, max_length=200),
    supplier: str | None = Query(None, max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[DisabilityContractRead]:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date")
    rows = await repository.disability_contracts(
        start_date=start_date,
        end_date=end_date,
        organism=organism,
        supplier=supplier,
        offset=offset,
        limit=limit,
    )
    return [DisabilityContractRead.model_validate(row) for row in rows]


@router.get(
    "/prices/items",
    response_model=list[PriceItemRead],
    summary="Real procurement line items matching a product search",
    description="Real `core.licitacion_item` rows (unit price, quantity, unit) matching a free-text "
    "search over the item's own nombre/descripcion, optionally scoped to a categoria_id, for "
    "price-benchmarking. There is no brand/material/capacity data in core.* to filter by instead.",
)
async def price_items(
    q: str = Query(..., min_length=2, max_length=200),
    categoria_id: int | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),

    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[PriceItemRead]:
    rows = await repository.price_items(
        q=q, categoria_id=categoria_id, licitacion_ids=licitacion_ids, limit=limit
    )
    return [PriceItemRead.model_validate(row) for row in rows]


@router.get(
    "/market-objective",
    response_model=MarketObjectiveRead,
    summary="Mercado Objetivo: Discapacidad & Geriatría",
    description="Real KPIs, monthly trend, leading buyers/suppliers and related categories for tenders "
    "matching the geriatría/discapacidad domain dictionary (app/nlp/dictionary.py), computed from "
    "core.licitacion/core.adjudicacion. With `segmento`, scoped to that rubro/concept instead.",
)
async def market_objective(
    segmento: Segmento | None = Depends(get_segmento),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> MarketObjectiveRead:
    summary = await repository.market_objective_summary(
        terms=segmento.terms if segmento else None, licitacion_ids=licitacion_ids
    )
    return MarketObjectiveRead.model_validate(summary)


@router.get(
    "/competition/summary",
    response_model=CompetitionSummaryRead,
    summary="Competitive-intensity summary",
    description="Average bidders per award, average discount vs. estimated amount, and a bidder-count "
    "distribution, computed from `core.adjudicacion` (only awards that report those fields).",
)
async def competition_summary(
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> CompetitionSummaryRead:
    summary = await repository.competition_summary(licitacion_ids=licitacion_ids)
    return CompetitionSummaryRead.model_validate(summary)


@router.get(
    "/quality/missing-keys",
    response_model=list[DataQualityMissingKeysRead],
    summary="Data-quality missing-key indicators",
    description="Counts of canonical records missing expected keys, surfaced for ETL "
    "data-quality monitoring.",
)
async def quality_missing_keys(
    repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[DataQualityMissingKeysRead]:
    rows = await repository.data_quality_missing_keys()
    return [DataQualityMissingKeysRead.model_validate(row) for row in rows]


@router.post(
    "/adjudicaciones/ingest-by-date",
    response_model=AdjudicacionesPersistenceSummaryResponse,
    tags=["Analytics"],
    summary="Score and persist adjudicaciones for a date",
    description="Fetches adjudicaciones from ChileCompra for the given `fecha`, scores "
    "opportunity/risk, and persists the resulting snapshots.",
)
async def ingest_adjudicaciones_analytics_by_date(
    payload: PersistAdjudicacionesByDateRequest,
    use_case: AdjudicacionAnalyticsUseCase = Depends(
        get_adjudicacion_analytics_use_case
    ),
) -> AdjudicacionesPersistenceSummaryResponse:
    result = await use_case.persist_by_date(
        PersistAnalyticsByDateInput(fecha=payload.fecha, config=payload.config)
    )
    return AdjudicacionesPersistenceSummaryResponse(
        persisted_items=result.summary.scored_items,
        outlier_items=result.summary.outlier_items,
        avg_opportunity_score=result.summary.avg_opportunity_score,
        risk_distribution=result.summary.risk_distribution,
    )


@router.post(
    "/adjudicaciones/ingest-by-query",
    response_model=AdjudicacionesPersistenceSummaryResponse,
    tags=["Analytics"],
    summary="Score and persist adjudicaciones matching a query",
    description="Fetches adjudicaciones from ChileCompra matching an arbitrary search "
    "`query`, scores opportunity/risk, and persists the resulting snapshots under "
    "`snapshot_date`.",
)
async def ingest_adjudicaciones_analytics_by_query(
    payload: PersistAdjudicacionesByQueryRequest,
    use_case: AdjudicacionAnalyticsUseCase = Depends(
        get_adjudicacion_analytics_use_case
    ),
) -> AdjudicacionesPersistenceSummaryResponse:
    result = await use_case.persist_by_query(
        PersistAnalyticsByQueryInput(
            query=payload.query,
            snapshot_date=payload.snapshot_date,
            config=payload.config,
        )
    )
    return AdjudicacionesPersistenceSummaryResponse(
        persisted_items=result.summary.scored_items,
        outlier_items=result.summary.outlier_items,
        avg_opportunity_score=result.summary.avg_opportunity_score,
        risk_distribution=result.summary.risk_distribution,
    )


@router.get(
    "/adjudicaciones/{external_id}/history",
    response_model=list[AdjudicacionAnalyticsSnapshotRead],
    tags=["Analytics"],
    summary="Snapshot history for an adjudicacion",
    description="Returns every persisted opportunity/risk snapshot for `external_id`, "
    "most recent first, capped at `limit`.",
)
def adjudicaciones_analytics_history(
    external_id: str,
    limit: int = Query(50, ge=1, description="Maximum number of snapshots to return."),
    use_case: AdjudicacionAnalyticsUseCase = Depends(
        get_adjudicacion_analytics_use_case
    ),
) -> list[AdjudicacionAnalyticsSnapshotRead]:
    history = use_case.history(external_id=external_id, limit=limit)
    return [_snapshot_read(item) for item in history]


@router.get(
    "/adjudicaciones/{external_id}/latest",
    response_model=AdjudicacionAnalyticsSnapshotRead,
    tags=["Analytics"],
    summary="Latest snapshot for an adjudicacion",
    responses={404: {"description": "No snapshot exists for this external_id."}},
)
def adjudicaciones_analytics_latest(
    external_id: str,
    use_case: AdjudicacionAnalyticsUseCase = Depends(
        get_adjudicacion_analytics_use_case
    ),
) -> AdjudicacionAnalyticsSnapshotRead:
    latest = use_case.latest(external_id=external_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="Analytics snapshot not found")
    return _snapshot_read(latest)


@router.get(
    "/adjudicaciones/timeseries",
    response_model=list[AdjudicacionesTimeseriesPointResponse],
    tags=["Analytics"],
    summary="Daily adjudicaciones timeseries",
    description="Aggregates persisted snapshots by day within `[start_date, end_date]`: "
    "totals, outliers, degraded-source ratio and risk distribution per day.",
)
def adjudicaciones_analytics_timeseries(
    start_date: date,
    end_date: date,
    use_case: AdjudicacionAnalyticsUseCase = Depends(
        get_adjudicacion_analytics_use_case
    ),
) -> list[AdjudicacionesTimeseriesPointResponse]:
    try:
        points = use_case.timeseries(start_date=start_date, end_date=end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return [
        AdjudicacionesTimeseriesPointResponse.model_validate(point) for point in points
    ]


@router.get(
    "/adjudicaciones/dashboard",
    response_model=AdjudicacionesDashboardSummaryResponse,
    tags=["Analytics"],
    summary="Adjudicaciones dashboard summary",
    description="Aggregate opportunity/risk dashboard over `[start_date, end_date]`, with "
    "optional filters (`risk_level`, `only_degraded`, `only_outliers`) and a paginated, "
    "sortable breakdown by source and by organism.",
)
def adjudicaciones_analytics_dashboard(
    start_date: date,
    end_date: date,
    limit: int = 10,
    risk_level: str | None = None,
    only_degraded: bool = False,
    only_outliers: bool = False,
    breakdown_limit: int | None = None,
    breakdown_sort_by: Literal[
        "total_items", "outlier_ratio", "degraded_ratio", "avg_opportunity_score"
    ] = "total_items",
    breakdown_desc: bool = True,
    min_total_items: int | None = None,
    min_degraded_ratio: float | None = None,
    breakdown_page: int = 1,
    breakdown_page_size: int | None = None,
    use_case: AdjudicacionAnalyticsUseCase = Depends(
        get_adjudicacion_analytics_use_case
    ),
) -> AdjudicacionesDashboardSummaryResponse:
    try:
        summary = use_case.dashboard_summary(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            risk_level=risk_level,
            only_degraded=only_degraded,
            only_outliers=only_outliers,
            breakdown_limit=breakdown_limit,
            breakdown_sort_by=breakdown_sort_by,
            breakdown_desc=breakdown_desc,
            min_total_items=min_total_items,
            min_degraded_ratio=min_degraded_ratio,
            breakdown_page=breakdown_page,
            breakdown_page_size=breakdown_page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AdjudicacionesDashboardSummaryResponse.model_validate(summary)


def _snapshot_read(item) -> AdjudicacionAnalyticsSnapshotRead:
    source_filters = item.source_filters or {}
    return AdjudicacionAnalyticsSnapshotRead.model_validate(
        {
            **asdict(item),
            "is_degraded_source": source_filters.get("degraded_source") == "true",
            "source_resource": source_filters.get("source_resource"),
        }
    )
