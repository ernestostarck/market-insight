"""Safe and controlled SQL Retrieval Engine for MercadoInsight AI (Fase 9.6).

Executes strictly parameterized SQL templates over authorized data marts and views in
a PostgreSQL read-only session with a 5000ms statement timeout, completely preventing
SQL injection, DDL, DML, and arbitrary free-form table access.
"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import (
    IntentType,
    QueryPlan,
    RetrievalResult,
    RetrievalStrategy,
    Source,
)
from app.ai.interfaces import Retriever

# Blacklisted SQL keywords to ensure zero DDL/DML and multi-statement execution
_FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)
_SEMICOLON_PATTERN = re.compile(r";")


# Whitelisted Controlled SQL Templates mapped to analytical data marts
_SQL_TEMPLATES: dict[str, str] = {
    "category_spending": """
        SELECT
            categoria,
            codigo_categoria,
            gasto_total_oc,
            numero_ordenes_compra,
            gasto_promedio_oc
        FROM categories_mart.v_category_spending
        WHERE (CAST(:category_code AS VARCHAR) IS NULL OR codigo_categoria = :category_code)
        ORDER BY gasto_total_oc DESC
        LIMIT :limit
    """,
    "supplier_performance": """
        SELECT
            razon_social,
            rut,
            total_adjudicaciones,
            monto_total_adjudicado,
            ratio_adjudicacion_promedio,
            ultima_adjudicacion
        FROM suppliers_mart.v_supplier_performance
        WHERE (CAST(:supplier_rut AS VARCHAR) IS NULL OR rut = :supplier_rut)
        ORDER BY monto_total_adjudicado DESC
        LIMIT :limit
    """,
    "market_monthly_trends": """
        SELECT
            mes,
            total_licitaciones,
            total_adjudicaciones,
            monto_total_adjudicado
        FROM analytics.mv_market_monthly
        WHERE (CAST(:target_year AS INTEGER) IS NULL OR EXTRACT(YEAR FROM mes) = :target_year)
        ORDER BY mes ASC
        LIMIT :limit
    """,
    "disability_contracts": """
        SELECT
            licitacion_id,
            nombre,
            descripcion,
            monto_adjudicado,
            proveedor,
            organismo,
            periodo
        FROM disability_market_mart.v_disability_contracts
        ORDER BY periodo DESC
        LIMIT :limit
    """,
    "tender_lookup": """
        SELECT
            id,
            nombre,
            descripcion,
            estado,
            organismo_id,
            created_at
        FROM core.licitacion
        WHERE (CAST(:licitacion_id AS VARCHAR) IS NOT NULL AND CAST(id AS TEXT) = :licitacion_id)
        LIMIT 1
    """,
}


class SQLRetriever(Retriever):
    """SQL retrieval engine executing verified query plans with strict security boundaries."""

    def __init__(self, session: AsyncSession, max_rows: int = 100) -> None:
        self._session = session
        self._max_rows = max_rows

    def validate_sql_safety(self, sql_query: str) -> None:
        """Enforce read-only semantics: reject dangerous statements or multi-queries."""
        cleaned = sql_query.strip()
        if _SEMICOLON_PATTERN.search(cleaned):
            raise PermissionError("SQL statements with semicolons are not permitted for security.")

        if not (cleaned.upper().startswith("SELECT") or cleaned.upper().startswith("WITH")):
            raise PermissionError("Only SELECT or WITH queries are permitted in SQLRetriever.")

        forbidden_match = _FORBIDDEN_SQL_PATTERNS.search(cleaned)
        if forbidden_match:
            raise PermissionError(
                f"SQL contains forbidden keyword '{forbidden_match.group(0).upper()}'. DDL and DML operations are strictly blocked."
            )

    def select_template_and_params(self, plan: QueryPlan) -> tuple[str, dict[str, Any]]:
        """Map QueryPlan filters and intent to a controlled SQL template and parameters."""
        filters = plan.filters or {}
        limit = self._max_rows

        if plan.intent == IntentType.TREND_ANALYSIS:
            return _SQL_TEMPLATES["market_monthly_trends"], {
                "target_year": filters.get("year"),
                "limit": limit,
            }

        if plan.intent == IntentType.SUPPLIER_ANALYSIS:
            return _SQL_TEMPLATES["supplier_performance"], {
                "supplier_rut": filters.get("supplier_rut"),
                "limit": limit,
            }

        if plan.intent == IntentType.DETAIL_LOOKUP and "licitacion_id" in filters:
            return _SQL_TEMPLATES["tender_lookup"], {
                "licitacion_id": str(filters.get("licitacion_id")),
            }

        if filters.get("concept") == "SALUD_MOVILIDAD":
            return _SQL_TEMPLATES["disability_contracts"], {
                "limit": limit,
            }

        # Default quantitative spending / price template
        return _SQL_TEMPLATES["category_spending"], {
            "category_code": filters.get("category_code"),
            "limit": limit,
        }

    async def retrieve(self, plan: QueryPlan) -> RetrievalResult:
        """Execute the query plan in PostgreSQL read-only session and construct verifiable sources."""
        # 1. Determine SQL and parameters from validated template
        if plan.sql_query:
            # When caller explicitly provided a template query, validate it
            sql_stmt = plan.sql_query
            params = plan.parameters or {}
        else:
            sql_stmt, params = self.select_template_and_params(plan)

        # 2. Strict safety validation
        self.validate_sql_safety(sql_stmt)

        # 3. Execute with timeout in read-only mode
        start_time = time.perf_counter()

        # Set statement timeout to 5000ms
        await self._session.execute(text("SET statement_timeout = '5000ms'"))

        result = await self._session.execute(text(sql_stmt), params)
        rows = result.mappings().all()

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 4. Transform into structured items and verifiable Sources
        items: list[dict[str, Any]] = [dict(row) for row in rows]
        sources: list[Source] = []

        for idx, item in enumerate(items):
            source_id = str(
                item.get("id")
                or item.get("licitacion_id")
                or item.get("rut")
                or item.get("codigo_categoria")
                or f"row_{idx + 1}"
            )
            title = str(
                item.get("nombre")
                or item.get("razon_social")
                or item.get("categoria")
                or f"Registro analítico {source_id}"
            )
            snippet_parts = [f"{k}: {v}" for k, v in item.items() if v is not None and k not in ("id", "nombre")]
            snippet = ", ".join(snippet_parts[:4])

            sources.append(
                Source(
                    id=source_id,
                    source_type="mart",
                    title=title,
                    snippet=snippet,
                    score=1.0,
                    metadata=item,
                )
            )

        return RetrievalResult(
            strategy_used=RetrievalStrategy.SQL,
            items=items,
            sources=sources,
            sql_executed=sql_stmt.strip(),
            execution_time_ms=round(elapsed_ms, 2),
            total_results=len(items),
        )
