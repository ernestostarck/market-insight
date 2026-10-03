"""Rule-based and pattern-matching Intent Detection for MercadoInsight AI (Fase 9.4).

Accurately classifies user intent into the 10 canonical intents:
- search
- spending_analysis
- comparison
- supplier_analysis
- organization_analysis
- price_analysis
- semantic_search
- trend_analysis
- detail_lookup
- unknown/out_of_scope
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.ai.contracts import ChatMessage, IntentType
from app.ai.interfaces import IntentDetector


def _normalize(text: str) -> str:
    """Normalize text: lowercase, strip accents, and remove excess whitespace."""
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Patterns for precise identifier matching
_TENDER_ID_PATTERN = re.compile(
    r"\b\d{1,6}-\d{1,4}-(?:L[RP]|CO|CM|LE|LP|B2|R1)\d{2,4}\b", re.IGNORECASE
)
_ORDER_ID_PATTERN = re.compile(
    r"\b\d{1,6}-\d{1,4}-(?:OC|SE)\d{2,4}\b", re.IGNORECASE
)
_RUT_PATTERN = re.compile(
    r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"
)
_YEAR_PATTERN = re.compile(r"\b(20[12]\d)\b")


# Lexical dictionaries for normalized intents
_PRICE_KEYWORDS = (
    "precio promedio",
    "precios promedio",
    "precio unitario",
    "precios unitarios",
    "costo unitario",
    "costo promedio",
    "a que precio",
    "cuanto cuesta",
    "cuanto costaron",
    "valor promedio",
    "valor unitario",
)

_SPENDING_KEYWORDS = (
    "cuanto gasto",
    "cuanto gastaron",
    "cuanto se gasto",
    "gasto total",
    "gastos totales",
    "monto total",
    "monto adjudicado",
    "montos adjudicados",
    "presupuesto ejecutado",
    "cuanto adjudico",
    "total gastado",
    "total adjudicado",
    "volumen de compra",
    "volumen de gasto",
)

_TREND_KEYWORDS = (
    "evolucion",
    "tendencia",
    "mes a mes",
    "mensualmente",
    "historico",
    "a lo largo del tiempo",
    "variacion mensual",
    "variacion interanual",
    "crecimiento",
    "comportamiento temporal",
)

_COMPARISON_KEYWORDS = (
    "comparar",
    "comparativa",
    "diferencia entre",
    "frente a",
    "en comparacion con",
    " versus ",
    " vs ",
    "cual gasto mas",
    "quien gasto mas",
    "quien vendio mas",
)

_SUPPLIER_KEYWORDS = (
    "proveedor",
    "proveedores",
    "adjudicatario",
    "adjudicatarios",
    "empresa adjudicada",
    "desempeno del proveedor",
    "quien gano la licitacion",
    "quienes ganaron la licitacion",
    "quien gano el contrato",
    "quien se adjudico",
    "quienes se adjudicaron",
    "ranking de proveedores",
    "principales vendedores",
)

_OUT_OF_SCOPE_TOPICS = (
    "futbol",
    "mundial",
    "receta",
    "chiste",
    "clima",
    "tiempo hoy",
    "temperatura",
    "pelicula",
    "horoscopo",
)

_ORGANIZATION_KEYWORDS = (
    "municipio",
    "municipios",
    "municipalidad",
    "municipalidades",
    "organismo",
    "organismos",
    "hospital",
    "hospitales",
    "ministerio",
    "ministerios",
    "comprador",
    "compradores",
    "entidad compradora",
    "servicio de salud",
)

_SEMANTIC_KEYWORDS = (
    "relacionado con",
    "relacionados con",
    "afines a",
    "afines de",
    "similar a",
    "similares a",
    "parecido a",
    "parecidos a",
    "movilidad asistida",
    "productos afines",
    "concepto",
    "conceptos",
    "especificaciones tecnicas de",
    "tecnologias similares",
)

_SEARCH_KEYWORDS = (
    "buscar",
    "busqueda",
    "encuentra",
    "encontrar",
    "mostrar",
    "dame licitaciones",
    "que licitaciones hay",
    "cuales son las licitaciones",
    "listar licitaciones",
)

_GREETING_PATTERNS = (
    "hola",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "como estas",
    "que tal",
    "chao",
    "adios",
    "gracias",
    "muchas gracias",
)


class RuleBasedIntentDetector(IntentDetector):
    """Deterministic intent detector combining pattern matching, regexes, and lexical heuristics."""

    def extract_entities(self, query: str) -> dict[str, Any]:
        """Extract explicit identifiers and entities from query text."""
        entities: dict[str, Any] = {}

        tender_match = _TENDER_ID_PATTERN.search(query)
        if tender_match:
            entities["tender_id"] = tender_match.group(0).upper()

        order_match = _ORDER_ID_PATTERN.search(query)
        if order_match:
            entities["order_id"] = order_match.group(0).upper()

        rut_match = _RUT_PATTERN.search(query)
        if rut_match:
            entities["rut"] = rut_match.group(0)

        year_matches = _YEAR_PATTERN.findall(query)
        if year_matches:
            entities["years"] = [int(y) for y in year_matches]

        return entities

    async def detect_intent(
        self,
        query: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> tuple[IntentType, float]:
        """Classify user query intent and return (IntentType, confidence_score)."""
        raw = query.strip()
        norm = _normalize(raw)

        if not norm:
            return IntentType.UNKNOWN, 0.0

        # 1. Check for explicit ID lookups (highest specificity)
        if _TENDER_ID_PATTERN.search(raw) or _ORDER_ID_PATTERN.search(raw):
            return IntentType.DETAIL_LOOKUP, 0.98

        # 2. Check for explicit out-of-scope trivia / topics
        if any(topic in norm for topic in _OUT_OF_SCOPE_TOPICS):
            return IntentType.UNKNOWN, 0.95

        # 3. Check for greetings or out of scope smalltalk
        is_greeting = any(norm == g or norm.startswith(f"{g} ") for g in _GREETING_PATTERNS)
        if is_greeting and len(norm.split()) <= 4:
            return IntentType.UNKNOWN, 0.95

        # 3. Check for comparison intent
        if any(kw in norm for kw in _COMPARISON_KEYWORDS):
            return IntentType.COMPARISON, 0.92

        # 4. Check for trend / temporal analysis
        if any(kw in norm for kw in _TREND_KEYWORDS):
            return IntentType.TREND_ANALYSIS, 0.90

        # 5. Check for price analysis
        if any(kw in norm for kw in _PRICE_KEYWORDS):
            return IntentType.PRICE_ANALYSIS, 0.92

        # 6. Check for spending analysis (quantitative expenditures)
        if any(kw in norm for kw in _SPENDING_KEYWORDS):
            return IntentType.SPENDING_ANALYSIS, 0.95

        # 7. Check for semantic / conceptual similarity search
        if any(kw in norm for kw in _SEMANTIC_KEYWORDS):
            return IntentType.SEMANTIC_SEARCH, 0.90

        # 8. Check for supplier analysis
        if any(kw in norm for kw in _SUPPLIER_KEYWORDS) or _RUT_PATTERN.search(raw):
            return IntentType.SUPPLIER_ANALYSIS, 0.88

        # 9. Check for organization analysis
        if any(kw in norm for kw in _ORGANIZATION_KEYWORDS):
            # If the question asks about general activity or purchases of an organization
            return IntentType.ORGANIZATION_ANALYSIS, 0.85

        # 10. Check for general search
        if any(kw in norm for kw in _SEARCH_KEYWORDS):
            return IntentType.SEARCH, 0.80

        # Fallback: check if query contains procurement domain keywords
        domain_terms = ("licitacion", "licitaciones", "compra", "adquisicion", "orden de compra", "chilecompra")
        if any(dt in norm for dt in domain_terms):
            return IntentType.SEARCH, 0.65

        # If completely unmapped, mark as unknown/out_of_scope
        return IntentType.UNKNOWN, 0.40
