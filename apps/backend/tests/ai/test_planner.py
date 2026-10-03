"""Unit tests for Query Planning (Fase 9.5).

Tests deterministic query planning, metric/dimension validation, time range normalization,
and strategy assignment without free-form LLM SQL.
"""

from __future__ import annotations

import pytest

from app.ai.contracts import IntentType, RetrievalStrategy, UnsupportedMetricError
from app.ai.interfaces import QueryPlanner
from app.ai.planner import DeterministicQueryPlanner


@pytest.fixture
def planner() -> DeterministicQueryPlanner:
    return DeterministicQueryPlanner()


def test_planner_satisfies_protocol(planner: DeterministicQueryPlanner) -> None:
    assert isinstance(planner, QueryPlanner)


@pytest.mark.asyncio
async def test_plan_spending_analysis_routes_to_sql(planner: DeterministicQueryPlanner) -> None:
    query = "¿Cuánto gastaron los municipios en sillas de ruedas durante 2025?"
    plan = await planner.plan_query(query, intent=IntentType.SPENDING_ANALYSIS)

    assert plan.intent == IntentType.SPENDING_ANALYSIS
    assert plan.retrieval_strategy == RetrievalStrategy.SQL
    assert plan.time_range.get("year") == 2025
    assert plan.filters.get("year") == 2025
    assert plan.filters.get("organization_type") == "municipality"
    assert "SALUD_MOVILIDAD" in plan.normalized_concepts
    assert "total_monto_adjudicado" in plan.metrics
    assert "gasto_total_oc" in plan.metrics
    assert plan.semantic_query is None


@pytest.mark.asyncio
async def test_plan_semantic_search_routes_to_vector(planner: DeterministicQueryPlanner) -> None:
    query = "Encuentra productos relacionados con movilidad asistida"
    plan = await planner.plan_query(query, intent=IntentType.SEMANTIC_SEARCH)

    assert plan.intent == IntentType.SEMANTIC_SEARCH
    assert plan.retrieval_strategy == RetrievalStrategy.SEMANTIC
    assert plan.semantic_query == query
    assert len(plan.metrics) == 0


@pytest.mark.asyncio
async def test_plan_supplier_analysis(planner: DeterministicQueryPlanner) -> None:
    query = "Desempeño del proveedor con RUT 76.123.456-7"
    plan = await planner.plan_query(query, intent=IntentType.SUPPLIER_ANALYSIS)

    assert plan.intent == IntentType.SUPPLIER_ANALYSIS
    assert plan.retrieval_strategy == RetrievalStrategy.SQL
    assert plan.filters.get("supplier_rut") == "76.123.456-7"
    assert "proveedor_rut" in plan.dimensions
    assert "total_monto_adjudicado" in plan.metrics


@pytest.mark.asyncio
async def test_plan_trend_analysis(planner: DeterministicQueryPlanner) -> None:
    query = "Evolución mensual del gasto durante 2024"
    plan = await planner.plan_query(query, intent=IntentType.TREND_ANALYSIS)

    assert plan.intent == IntentType.TREND_ANALYSIS
    assert plan.retrieval_strategy == RetrievalStrategy.SQL
    assert "mes" in plan.dimensions
    assert "monto_total_adjudicado" in plan.metrics
    assert plan.filters.get("year") == 2024


@pytest.mark.asyncio
async def test_plan_search_with_filters_is_hybrid(planner: DeterministicQueryPlanner) -> None:
    query = "Buscar licitaciones de tecnología durante 2024"
    plan = await planner.plan_query(query, intent=IntentType.SEARCH)

    assert plan.intent == IntentType.SEARCH
    assert plan.retrieval_strategy == RetrievalStrategy.HYBRID
    assert plan.filters.get("year") == 2024
    assert plan.filters.get("category_code") == "TECNOLOGIA"
    assert plan.semantic_query == query


@pytest.mark.asyncio
async def test_plan_out_of_scope_is_direct(planner: DeterministicQueryPlanner) -> None:
    query = "Hola, buenas tardes"
    plan = await planner.plan_query(query, intent=IntentType.UNKNOWN)

    assert plan.intent == IntentType.UNKNOWN
    assert plan.retrieval_strategy == RetrievalStrategy.DIRECT
    assert plan.semantic_query is None


def test_validate_metrics_rejects_unsupported(planner: DeterministicQueryPlanner) -> None:
    with pytest.raises(UnsupportedMetricError) as exc_info:
        planner.validate_metrics(["total_monto_adjudicado", "roi_inversion_ficticia"])

    assert "roi_inversion_ficticia" in str(exc_info.value)
    assert "no está soportada" in str(exc_info.value)


def test_validate_dimensions_rejects_unsupported(planner: DeterministicQueryPlanner) -> None:
    with pytest.raises(ValueError) as exc_info:
        planner.validate_dimensions(["comprador_nombre", "dimension_inexistente"])

    assert "dimension_inexistente" in str(exc_info.value)
    assert "no es válida" in str(exc_info.value)
