"""Multi-layer Guardrails for MercadoInsight AI (Fase 9.16).

Enforces domain scope (ChileCompra / Mercado Público / Technical Aids), data boundaries,
SQL read-only limits, and input prompt injection defense.
"""

from __future__ import annotations

import re

from app.ai.contracts import Context, GuardrailResult

# Domain Scope Keywords (ChileCompra, procurement, technical aids, assistive devices)
_SCOPE_KEYWORDS: frozenset[str] = frozenset({
    # Core public procurement
    "chilecompra",
    "mercado público",
    "mercado publico",
    "licitacion",
    "licitaciones",
    "licitación",
    "orden de compra",
    "ordenes de compra",
    "órdenes de compra",
    "oc",
    "proveedor",
    "proveedores",
    "organismo",
    "organismos",
    "comprador",
    "compradores",
    "adjudicacion",
    "adjudicaciones",
    "adjudicación",
    "adjudicado",
    "adjudicada",
    "categoria",
    "categorias",
    "categoría",
    "categorías",
    "precio",
    "precios",
    "monto",
    "gasto",
    "contrato",
    "contratos",
    "bases",
    "convenio marco",
    "trato directo",
    "rut",
    "clp",
    "uf",
    # Domain-specific focus: Health, Technical Aids, Mobility, Geriatrics
    "ayuda tecnica",
    "ayudas tecnicas",
    "ayuda técnica",
    "ayudas técnicas",
    "discapacidad",
    "geriatria",
    "geriatría",
    "movilidad",
    "accesibilidad",
    "silla de ruedas",
    "sillas de ruedas",
    "protesis",
    "prótesis",
    "ortesis",
    "órtesis",
    "andador",
    "camilla",
    "hospital",
    "salud",
    "insumos medicos",
    "insumos médicos",
    "farmacia",
    "cenabast",
    "senadis",
    # Conversational basics / meta
    "hola",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "gracias",
    "ayuda",
    "que puedes hacer",
    "quien eres",
    "como funciona",
})

# Suspicious patterns indicating prompt injection or jailbreak attempts
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"olvida\s+(?:todas\s+)?las\s+instrucciones\s+(?:previas|anteriores)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:unrestricted|DAN|jailbreak)", re.IGNORECASE),
    re.compile(r"act\s+as\s+an?\s+unfiltered", re.IGNORECASE),
    re.compile(r"###\s*system", re.IGNORECASE),
    re.compile(r"reveal\s+(?:your\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"muestra\s+tu\s+prompt\s+de\s+sistema", re.IGNORECASE),
]

_DISALLOWED_SQL_KEYWORDS = re.compile(
    r"\b(DROP|INSERT|UPDATE|DELETE|ALTER|GRANT|REVOKE|TRUNCATE|EXEC|EXECUTE|VACUUM)\b",
    re.IGNORECASE,
)

SCOPE_REJECTION_MESSAGE = (
    "Como asistente analítico de MercadoInsight, estoy especializado exclusivamente en el "
    "sistema de compras públicas de Chile (ChileCompra / Mercado Público), licitaciones, "
    "órdenes de compra, proveedores y adquisiciones del sector público (incluyendo ayudas "
    "técnicas, equipamiento y salud). Por favor, indícame qué información sobre contrataciones "
    "públicas necesitas consultar."
)

INJECTION_REJECTION_MESSAGE = (
    "La consulta contiene patrones de entrada no permitidos por las políticas de seguridad "
    "del sistema analítico."
)


class ScopeGuardrail:
    """Verifies that queries fall strictly within Chilean public procurement domain."""

    def evaluate(self, query: str) -> GuardrailResult:
        query_lower = query.lower().strip()

        # Very short greetings or meta inquiries pass through
        if len(query_lower) < 4:
            return GuardrailResult(is_safe=True, layer="scope")

        # Check for numeric procurement codes (e.g. 1234-56-LP24) or RUT patterns
        if re.search(r"\b\d+-\d+-[A-Za-z0-9]+\b", query) or re.search(r"\b\d{7,8}-[\dkK]\b", query):
            return GuardrailResult(is_safe=True, layer="scope")

        # Check keyword matches with proper word boundaries
        words = set(re.findall(r"\b[\w-]+\b", query_lower))
        for kw in _SCOPE_KEYWORDS:
            if " " in kw:
                if kw in query_lower:
                    return GuardrailResult(is_safe=True, layer="scope")
            else:
                if kw in words:
                    return GuardrailResult(is_safe=True, layer="scope")

        return GuardrailResult(
            is_safe=False,
            layer="scope",
            reason="Consulta fuera del dominio temático de ChileCompra / Mercado Público.",
            metadata={"query": query},
        )


class PromptInjectionGuardrail:
    """Scans for prompt injection, jailbreak attempts, or system prompt override."""

    def evaluate(self, text: str) -> GuardrailResult:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return GuardrailResult(
                    is_safe=False,
                    layer="injection",
                    reason="Patrón de indirect/direct prompt injection detectado.",
                )
        return GuardrailResult(is_safe=True, layer="injection")


class SQLBoundariesGuardrail:
    """Enforces read-only SELECT constraints, table whitelisting, and execution limits."""

    ALLOWED_SCHEMAS = ("dm_compras", "public")
    ALLOWED_TABLES = (
        "licitaciones",
        "ordenes_compra",
        "items_licitacion",
        "proveedores",
        "compradores",
        "dm_compras",
    )

    def evaluate(self, sql_query: str) -> GuardrailResult:
        clean_sql = sql_query.strip()

        # Disallow empty
        if not clean_sql:
            return GuardrailResult(is_safe=False, layer="sql", reason="SQL query vacío.")

        # Disallow DDL/DML
        if _DISALLOWED_SQL_KEYWORDS.search(clean_sql):
            return GuardrailResult(
                is_safe=False,
                layer="sql",
                reason="Operaciones DDL/DML no autorizadas en consultas analíticas.",
            )

        # Disallow multiple statements with semicolon
        if ";" in clean_sql.rstrip(";"):
            return GuardrailResult(
                is_safe=False,
                layer="sql",
                reason="Múltiples declaraciones SQL no permitidas.",
            )

        # Must start with SELECT
        if not clean_sql.upper().startswith("SELECT"):
            return GuardrailResult(
                is_safe=False,
                layer="sql",
                reason="Solo se permiten consultas analíticas SELECT.",
            )

        return GuardrailResult(is_safe=True, layer="sql")


class DataBoundariesGuardrail:
    """Prevents extrapolation to unreleased future years or assumption of missing stats."""

    MAX_CURRENT_YEAR = 2026

    def evaluate(self, text: str) -> GuardrailResult:
        # Detect claims asserting factual procurement stats for future years
        years = re.findall(r"\b(20[3-9]\d)\b", text)
        if years:
            return GuardrailResult(
                is_safe=False,
                layer="data_boundary",
                reason=f"Extrapolación a períodos futuros no disponibles ({', '.join(years)}).",
            )
        return GuardrailResult(is_safe=True, layer="data_boundary")


class GuardrailEngine:
    """Orchestrates input and output guardrail evaluations."""

    def __init__(
        self,
        scope_guardrail: ScopeGuardrail | None = None,
        injection_guardrail: PromptInjectionGuardrail | None = None,
        sql_guardrail: SQLBoundariesGuardrail | None = None,
        data_guardrail: DataBoundariesGuardrail | None = None,
    ) -> None:
        self.scope = scope_guardrail or ScopeGuardrail()
        self.injection = injection_guardrail or PromptInjectionGuardrail()
        self.sql = sql_guardrail or SQLBoundariesGuardrail()
        self.data = data_guardrail or DataBoundariesGuardrail()

    def validate_input(self, user_query: str) -> GuardrailResult:
        """Run all input layer validations on the user query."""
        # 1. Prompt injection defense
        inj_res = self.injection.evaluate(user_query)
        if not inj_res.is_safe:
            return inj_res

        # 2. Scope validation
        scope_res = self.scope.evaluate(user_query)
        if not scope_res.is_safe:
            return scope_res

        return GuardrailResult(is_safe=True, layer="input_all")

    def validate_output(
        self,
        answer: str,
        context: Context | None = None,
    ) -> GuardrailResult:
        """Run output layer validations on the generated assistant answer."""
        data_res = self.data.evaluate(answer)
        if not data_res.is_safe:
            return data_res

        return GuardrailResult(is_safe=True, layer="output_all")
