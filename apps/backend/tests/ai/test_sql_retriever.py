"""Unit tests for SQLRetriever (Fase 9.6).

Tests parametrized template selection, read-only safety guardrails, DDL/DML rejection,
and structured Source citation assembly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.contracts import IntentType, QueryPlan, RetrievalStrategy
from app.ai.interfaces import Retriever
from app.ai.sql_retriever import SQLRetriever


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def retriever(mock_session: AsyncMock) -> SQLRetriever:
    return SQLRetriever(session=mock_session, max_rows=50)


def test_sql_retriever_satisfies_protocol(retriever: SQLRetriever) -> None:
    assert isinstance(retriever, Retriever)


def test_validate_sql_safety_allows_safe_select(retriever: SQLRetriever) -> None:
    safe_queries = [
        "SELECT * FROM categories_mart.v_category_spending WHERE codigo_categoria = 'SALUD'",
        "WITH monthly AS (SELECT mes, monto FROM analytics.mv_market_monthly) SELECT * FROM monthly",
    ]
    for q in safe_queries:
        retriever.validate_sql_safety(q)  # Should not raise


def test_validate_sql_safety_rejects_ddl_and_dml(retriever: SQLRetriever) -> None:
    forbidden_queries = [
        "DROP TABLE core.licitacion",
        "DELETE FROM core.licitacion WHERE id = 1",
        "UPDATE core.licitacion SET estado = 'Cancelada'",
        "INSERT INTO core.licitacion (id) VALUES (1)",
        "ALTER TABLE core.licitacion DROP COLUMN nombre",
        "TRUNCATE core.licitacion",
        "GRANT ALL PRIVILEGES ON DATABASE mercado TO user",
    ]
    for q in forbidden_queries:
        with pytest.raises(PermissionError) as exc_info:
            retriever.validate_sql_safety(q)
        assert "strictly blocked" in str(exc_info.value) or "Only SELECT" in str(exc_info.value)


def test_validate_sql_safety_rejects_semicolon(retriever: SQLRetriever) -> None:
    injection_query = "SELECT * FROM core.licitacion; DROP TABLE users"
    with pytest.raises(PermissionError) as exc_info:
        retriever.validate_sql_safety(injection_query)
    assert "semicolons are not permitted" in str(exc_info.value)


def test_template_selection(retriever: SQLRetriever) -> None:
    # 1. Trend analysis
    plan_trend = QueryPlan(
        intent=IntentType.TREND_ANALYSIS,
        retrieval_strategy=RetrievalStrategy.SQL,
        filters={"year": 2024},
    )
    sql, params = retriever.select_template_and_params(plan_trend)
    assert "mv_market_monthly" in sql
    assert params["target_year"] == 2024

    # 2. Supplier analysis
    plan_supplier = QueryPlan(
        intent=IntentType.SUPPLIER_ANALYSIS,
        retrieval_strategy=RetrievalStrategy.SQL,
        filters={"supplier_rut": "76.123.456-7"},
    )
    sql, params = retriever.select_template_and_params(plan_supplier)
    assert "v_supplier_performance" in sql
    assert params["supplier_rut"] == "76.123.456-7"

    # 3. Disability concept
    plan_disability = QueryPlan(
        intent=IntentType.SPENDING_ANALYSIS,
        retrieval_strategy=RetrievalStrategy.SQL,
        filters={"concept": "SALUD_MOVILIDAD"},
    )
    sql, _ = retriever.select_template_and_params(plan_disability)
    assert "v_disability_contracts" in sql

    # 4. Detail lookup
    plan_lookup = QueryPlan(
        intent=IntentType.DETAIL_LOOKUP,
        retrieval_strategy=RetrievalStrategy.SQL,
        filters={"licitacion_id": "721-12-LP24"},
    )
    sql, params = retriever.select_template_and_params(plan_lookup)
    assert "core.licitacion" in sql
    assert params["licitacion_id"] == "721-12-LP24"


@pytest.mark.asyncio
async def test_retrieve_executes_and_constructs_sources(
    retriever: SQLRetriever, mock_session: AsyncMock
) -> None:
    # Setup mock row results
    mock_row_1 = {
        "codigo_categoria": "SALUD",
        "categoria": "Salud y Farmacia",
        "gasto_total_oc": 1250000000.0,
        "numero_ordenes_compra": 450,
        "gasto_promedio_oc": 2777777.7,
    }
    mock_row_2 = {
        "codigo_categoria": "TECNOLOGIA",
        "categoria": "Tecnología e Informática",
        "gasto_total_oc": 850000000.0,
        "numero_ordenes_compra": 310,
        "gasto_promedio_oc": 2741935.4,
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [mock_row_1, mock_row_2]
    mock_session.execute.return_value = mock_result

    plan = QueryPlan(
        intent=IntentType.SPENDING_ANALYSIS,
        retrieval_strategy=RetrievalStrategy.SQL,
        filters={"category_code": "SALUD"},
    )

    result = await retriever.retrieve(plan)

    assert result.strategy_used == RetrievalStrategy.SQL
    assert result.total_results == 2
    assert len(result.items) == 2
    assert len(result.sources) == 2
    assert result.execution_time_ms >= 0.0
    assert "v_category_spending" in (result.sql_executed or "")

    src1 = result.sources[0]
    assert src1.id == "SALUD"
    assert src1.source_type == "mart"
    assert src1.title == "Salud y Farmacia"
    assert "1250000000" in (src1.snippet or "")
    assert src1.metadata["numero_ordenes_compra"] == 450
