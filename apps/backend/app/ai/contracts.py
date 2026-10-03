"""Pydantic contracts and data structures for MercadoInsight AI (Fase 9.1).

Defines reproducible, strictly-typed schemas for Intent Detection, Query Planning,
Retrieval, Evidence Synthesis, Grounding, and Chat Conversations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntentType(str, Enum):
    """Classified intent of a natural language user query."""

    SEARCH = "search"
    SPENDING_ANALYSIS = "spending_analysis"
    COMPARISON = "comparison"
    SUPPLIER_ANALYSIS = "supplier_analysis"
    ORGANIZATION_ANALYSIS = "organization_analysis"
    PRICE_ANALYSIS = "price_analysis"
    SEMANTIC_SEARCH = "semantic_search"
    TREND_ANALYSIS = "trend_analysis"
    DETAIL_LOOKUP = "detail_lookup"
    UNKNOWN = "unknown/out_of_scope"


class RetrievalStrategy(str, Enum):
    """Strategy to retrieve evidence required to answer the query."""

    SQL = "sql"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    DIRECT = "direct"


class MessageRole(str, Enum):
    """Role of a message participant in the conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationStatus(str, Enum):
    """Lifecycle status of a conversation."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"


class Source(BaseModel):
    """Verifiable source of information backing an answer."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique entity ID (e.g. tender code, RUT, order number, chunk ID).")
    source_type: str = Field(..., description="Type of evidence (tender, purchase_order, buyer, supplier, chunk, mart).")
    title: str = Field(..., description="Human-readable title or description.")
    url: str | None = Field(default=None, description="Direct URL or system deep-link.")
    snippet: str | None = Field(default=None, description="Relevant text excerpt or structured evidence.")
    score: float | None = Field(default=None, description="Relevance score or similarity metric.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional properties.")


SUPPORTED_METRICS: frozenset[str] = frozenset({
    "monto_total_adjudicado",
    "total_monto_adjudicado",
    "total_licitaciones",
    "total_adjudicaciones",
    "numero_ordenes_compra",
    "gasto_total_oc",
    "gasto_promedio_oc",
    "ratio_adjudicacion_promedio",
    "monto_promedio_licitacion",
    "count",
})

SUPPORTED_DIMENSIONS: frozenset[str] = frozenset({
    "comprador_nombre",
    "comprador_rut",
    "proveedor_razon_social",
    "proveedor_rut",
    "categoria",
    "codigo_categoria",
    "mes",
    "año",
    "region",
    "estado",
})


class UnsupportedMetricError(ValueError):
    """Raised when a query requests a metric not supported or authorized by the platform."""


class QueryPlan(BaseModel):
    """Deterministic plan formulated to retrieve required evidence."""

    intent: IntentType = Field(..., description="Classified intent.")
    retrieval_strategy: RetrievalStrategy = Field(..., description="Target retrieval engine.")
    sql_query: str | None = Field(default=None, description="Parametrized SQL query for quantitative analysis.")
    semantic_query: str | None = Field(default=None, description="Text for embedding and vector similarity.")
    filters: dict[str, Any] = Field(default_factory=dict, description="Metadata filters (year, buyer_rut, region).")
    dimensions: list[str] = Field(default_factory=list, description="Grouping dimensions for aggregation.")
    metrics: list[str] = Field(default_factory=list, description="Validated metrics to aggregate.")
    time_range: dict[str, Any] = Field(default_factory=dict, description="Temporal window (year, start_date, end_date).")
    detected_entities: list[dict[str, Any]] = Field(default_factory=list, description="Entities detected in user query.")
    normalized_concepts: list[str] = Field(default_factory=list, description="Domain concepts matched from taxonomy.")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Bound SQL/retrieval parameters.")
    rationale: str = Field(default="", description="Explanation of why this plan was chosen.")


class RetrievalResult(BaseModel):
    """Consolidated results returned by retrieval engines."""

    strategy_used: RetrievalStrategy = Field(..., description="Actual strategy executed.")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Raw retrieved records or chunks.")
    sources: list[Source] = Field(default_factory=list, description="Extracted citations and sources.")
    sql_executed: str | None = Field(default=None, description="Executed SQL query when applicable.")
    execution_time_ms: float = Field(default=0.0, description="Retrieval latency in milliseconds.")
    total_results: int = Field(default=0, description="Total matches found.")


class Context(BaseModel):
    """Assembled evidence context passed into the LLM prompt."""

    formatted_prompt_context: str = Field(..., description="Compiled context string for the prompt.")
    sources: list[Source] = Field(default_factory=list, description="All sources available in context.")
    structured_data: list[dict[str, Any]] | dict[str, Any] | None = Field(
        default=None, description="Optional structured tabular data."
    )
    token_estimate: int = Field(default=0, description="Approximate token count of context.")


class GroundingResult(BaseModel):
    """Validation that the generated answer is strictly grounded in retrieved evidence."""

    is_grounded: bool = Field(..., description="True if answer is supported by evidence without hallucinations.")
    grounding_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence coverage score from 0 to 1.")
    unsupported_claims: list[str] = Field(default_factory=list, description="Detected unsupported statements.")
    validated_sources: list[Source] = Field(default_factory=list, description="Sources legitimately referenced.")
    rationale: str = Field(default="", description="Explanation of the grounding evaluation.")


class ChatMessage(BaseModel):
    """Single message within a conversation."""

    id: UUID | None = Field(default=None, description="Message UUID.")
    conversation_id: UUID | None = Field(default=None, description="Parent conversation UUID.")
    role: MessageRole = Field(..., description="Role of the sender.")
    content: str = Field(..., description="Message text.")
    model: str | None = Field(default=None, description="LLM model identifier used for generation.")
    tokens_input: int | None = Field(default=None, description="Input tokens consumed.")
    tokens_output: int | None = Field(default=None, description="Output tokens generated.")
    latency_ms: float | None = Field(default=None, description="Generation latency in milliseconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata (sources, plan, grounding).")
    created_at: datetime | None = Field(default=None, description="Creation timestamp.")


class ConversationSession(BaseModel):
    """Active conversational session state."""

    id: UUID = Field(..., description="Conversation UUID.")
    user_id: UUID | None = Field(default=None, description="Owner user UUID (null for anonymous sessions).")
    title: str | None = Field(default=None, description="Conversation title or summary.")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="Session status.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Session metadata.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Citation(BaseModel):
    """Granular citation linking a specific claim to a verified source."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Citation identifier (e.g. cit-1 or tender code).")
    source_id: str = Field(..., description="Referenced entity ID (tender code, RUT, order number).")
    source_type: str = Field(default="tender", description="Evidence type (tender, purchase_order, buyer, supplier, mart).")
    title: str = Field(..., description="Title or human-readable description of source.")
    snippet: str | None = Field(default=None, description="Verifiable excerpt supporting the claim.")
    relevance: float | None = Field(default=None, description="Source relevance score [0, 1].")
    url: str | None = Field(default=None, description="External deep link if available.")
    claim_text: str | None = Field(default=None, description="Specific factual claim supported.")
    target_route: str | None = Field(default=None, description="Frontend SPA route (e.g. /licitaciones/:id).")
    is_verified: bool = Field(default=True, description="True if verified against retrieved context.")


class GuardrailResult(BaseModel):
    """Evaluation result from multi-layer guardrails."""

    model_config = ConfigDict(frozen=True)

    is_safe: bool = Field(..., description="True if query or answer satisfies safety policies.")
    layer: str = Field(default="scope", description="Guardrail layer evaluated (scope, injection, data_boundary, sql).")
    reason: str | None = Field(default=None, description="Explanation when guardrail triggers.")
    sanitized_query: str | None = Field(default=None, description="Sanitized query if modification applied.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional guardrail diagnostics.")


class GeneratedResponse(BaseModel):
    """Complete synthesized answer with citations, grounding, and diagnostics."""

    content: str = Field(..., description="Synthesized natural language answer text.")
    sources: list[Source] = Field(default_factory=list, description="All retrieved sources available.")
    citations: list[Citation] = Field(default_factory=list, description="Extracted citations linked to claims.")
    grounding: GroundingResult | None = Field(default=None, description="Factual grounding audit result.")
    guardrail: GuardrailResult | None = Field(default=None, description="Guardrail validation output.")
    latency_ms: float = Field(default=0.0, description="Total generation latency in milliseconds.")
    model: str | None = Field(default=None, description="LLM model identifier used.")
    token_usage: dict[str, int] = Field(default_factory=dict, description="Input/output token counts.")
