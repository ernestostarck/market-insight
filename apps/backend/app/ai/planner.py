"""Deterministic and controlled Query Planning for MercadoInsight AI (Fase 9.5).

Formulates validated QueryPlans specifying intent, retrieval mode, dimensions, metrics,
temporal windows, and filters, while strictly rejecting unsupported metrics and preventing
uncontrolled free-form SQL generation.
"""

from __future__ import annotations

import re
from typing import Any

from app.ai.contracts import (
    SUPPORTED_DIMENSIONS,
    SUPPORTED_METRICS,
    ChatMessage,
    IntentType,
    QueryPlan,
    RetrievalStrategy,
    UnsupportedMetricError,
)
from app.ai.intent import RuleBasedIntentDetector, _normalize
from app.ai.interfaces import QueryPlanner

# Common known categories and concept terms in ChileCompra
_KNOWN_CONCEPTS_MAP: dict[str, str] = {
    "silla de ruedas": "SALUD_MOVILIDAD",
    "sillas de ruedas": "SALUD_MOVILIDAD",
    "movilidad asistida": "SALUD_MOVILIDAD",
    "ambulancia": "VEHICULOS_EMERGENCIA",
    "ambulancias": "VEHICULOS_EMERGENCIA",
    "computador": "TECNOLOGIA_EQUIPOS",
    "computadores": "TECNOLOGIA_EQUIPOS",
    "notebook": "TECNOLOGIA_EQUIPOS",
    "notebooks": "TECNOLOGIA_EQUIPOS",
    "medicamento": "SALUD_MEDICAMENTOS",
    "medicamentos": "SALUD_MEDICAMENTOS",
    "paracetamol": "SALUD_FARMACOLOGIA",
    "insumos medicos": "SALUD_INSUMOS",
    "servidores": "TECNOLOGIA_INFRAESTRUCTURA",
    "software": "TECNOLOGIA_SOFTWARE",
    "alimentos": "ALIMENTACION_VIVERES",
    "seguridad": "SERVICIOS_VIGILANCIA",
    "limpieza": "SERVICIOS_ASEO",
    "obra": "INFRAESTRUCTURA_OBRAS",
    "obras": "INFRAESTRUCTURA_OBRAS",
}

_KNOWN_CATEGORIES_MAP: dict[str, str] = {
    "salud": "SALUD",
    "tecnologia": "TECNOLOGIA",
    "ti": "TECNOLOGIA",
    "obras": "OBRAS",
    "alimentos": "ALIMENTOS",
    "servicios": "SERVICIOS",
    "educacion": "EDUCACION",
}


class DeterministicQueryPlanner(QueryPlanner):
    """Planner creating safe, strictly-validated retrieval plans without free-form LLM SQL."""

    def __init__(self, intent_detector: RuleBasedIntentDetector | None = None) -> None:
        self._detector = intent_detector or RuleBasedIntentDetector()

    def validate_metrics(self, metrics: list[str]) -> None:
        """Validate that all requested metrics are supported and authorized."""
        for metric in metrics:
            if metric not in SUPPORTED_METRICS:
                raise UnsupportedMetricError(
                    f"La métrica '{metric}' no está soportada ni autorizada en el catálogo analítico."
                )

    def validate_dimensions(self, dimensions: list[str]) -> None:
        """Validate that all requested dimensions exist in the analytical catalog."""
        for dim in dimensions:
            if dim not in SUPPORTED_DIMENSIONS:
                raise ValueError(
                    f"La dimensión '{dim}' no es válida en el catálogo analítico."
                )

    async def plan_query(
        self,
        query: str,
        intent: IntentType,
        conversation_history: list[ChatMessage] | None = None,
    ) -> QueryPlan:
        """Formulate a deterministic QueryPlan with validation and safety constraints."""
        norm = _normalize(query)
        entities = self._detector.extract_entities(query)

        filters: dict[str, Any] = {}
        dimensions: list[str] = []
        metrics: list[str] = []
        time_range: dict[str, Any] = {}
        normalized_concepts: list[str] = []

        # 1. Temporal range extraction
        if entities.get("years"):
            target_year = entities["years"][0]
            time_range["year"] = target_year
            filters["year"] = target_year
        else:
            # Check for year pattern directly
            year_match = re.search(r"\b(20[12]\d)\b", query)
            if year_match:
                y = int(year_match.group(1))
                time_range["year"] = y
                filters["year"] = y

        # 2. Entity extraction (RUT, IDs)
        if "rut" in entities:
            filters["supplier_rut"] = entities["rut"]
            dimensions.append("proveedor_rut")

        if "tender_id" in entities:
            filters["licitacion_id"] = entities["tender_id"]

        if "order_id" in entities:
            filters["orden_compra_id"] = entities["order_id"]

        # 3. Normalized concepts and category matching
        for term, code in _KNOWN_CONCEPTS_MAP.items():
            if term in norm:
                normalized_concepts.append(code)
                filters["concept"] = code
                break

        for cat_term, cat_code in _KNOWN_CATEGORIES_MAP.items():
            if cat_term in norm:
                filters["category_code"] = cat_code
                break

        # Organization type detection
        if any(w in norm for w in ("municipio", "municipios", "municipalidad", "municipalidades")):
            filters["organization_type"] = "municipality"
        elif any(w in norm for w in ("hospital", "hospitales", "servicio de salud")):
            filters["organization_type"] = "health_service"
        elif any(w in norm for w in ("ministerio", "ministerios")):
            filters["organization_type"] = "ministry"

        # 4. Strategy & Metrics Determination according to Intent
        if intent == IntentType.SPENDING_ANALYSIS:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["total_monto_adjudicado", "gasto_total_oc"]
            if "category_code" in filters or "concept" in filters:
                dimensions.append("categoria")
            if "organization_type" in filters:
                dimensions.append("comprador_nombre")
            rationale = "Consulta cuantitativa de gasto agregada sobre marts analíticos."

        elif intent == IntentType.PRICE_ANALYSIS:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["gasto_promedio_oc", "monto_promedio_licitacion"]
            dimensions.append("categoria")
            rationale = "Análisis de precios y montos promedio unitarios sobre data marts."

        elif intent == IntentType.SUPPLIER_ANALYSIS:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["total_monto_adjudicado", "total_adjudicaciones", "ratio_adjudicacion_promedio"]
            dimensions.append("proveedor_razon_social")
            rationale = "Análisis de adjudicaciones y desempeño de proveedores en v_supplier_performance."

        elif intent == IntentType.ORGANIZATION_ANALYSIS:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["total_monto_adjudicado", "total_licitaciones"]
            dimensions.append("comprador_nombre")
            rationale = "Análisis de compras y licitaciones agregadas por entidad compradora."

        elif intent == IntentType.TREND_ANALYSIS:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["total_licitaciones", "total_adjudicaciones", "monto_total_adjudicado"]
            dimensions.append("mes")
            rationale = "Evolución cronológica temporal sobre mv_market_monthly."

        elif intent == IntentType.COMPARISON:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["total_monto_adjudicado", "total_licitaciones"]
            dimensions.extend(["comprador_nombre", "mes"])
            rationale = "Comparativa estructurada de gasto y volumen transaccional."

        elif intent == IntentType.DETAIL_LOOKUP:
            retrieval_strategy = RetrievalStrategy.SQL
            metrics = ["count"]
            rationale = "Búsqueda puntual de registro estructurado por identificador unívoco."

        elif intent == IntentType.SEMANTIC_SEARCH:
            retrieval_strategy = RetrievalStrategy.SEMANTIC
            rationale = "Búsqueda conceptual y similitud vectorial en pgvector."

        elif intent == IntentType.SEARCH:
            # If query has structured filters (e.g. year, category) and text, use Hybrid
            if filters:
                retrieval_strategy = RetrievalStrategy.HYBRID
                rationale = "Búsqueda híbrida combinando filtros estructurados y búsqueda léxica/semántica."
            else:
                retrieval_strategy = RetrievalStrategy.SEMANTIC
                rationale = "Búsqueda semántica sobre especificaciones técnicas."

        else:  # UNKNOWN / OUT OF SCOPE
            retrieval_strategy = RetrievalStrategy.DIRECT
            rationale = "Consulta directa sin necesidad de retrieval (fuera de dominio o saludo)."

        # Deduplicate dimensions
        dimensions = list(dict.fromkeys(dimensions))

        # Validate that dimensions and metrics are compliant
        self.validate_metrics(metrics)
        self.validate_dimensions(dimensions)

        # Build clean semantic query when relevant
        semantic_query = query if retrieval_strategy in (RetrievalStrategy.SEMANTIC, RetrievalStrategy.HYBRID) else None

        return QueryPlan(
            intent=intent,
            retrieval_strategy=retrieval_strategy,
            semantic_query=semantic_query,
            filters=filters,
            dimensions=dimensions,
            metrics=metrics,
            time_range=time_range,
            detected_entities=[{"key": k, "value": v} for k, v in entities.items()],
            normalized_concepts=normalized_concepts,
            rationale=rationale,
        )
