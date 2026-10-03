"""Tests for AI Pydantic contracts and abstract protocols (Fase 9.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.ai.contracts import (
    ChatMessage,
    Context,
    ConversationSession,
    ConversationStatus,
    GroundingResult,
    IntentType,
    MessageRole,
    QueryPlan,
    RetrievalResult,
    RetrievalStrategy,
    Source,
)
from app.ai.interfaces import (
    ContextBuilder,
    GroundingValidator,
    IntentDetector,
    LLMGateway,
    QueryPlanner,
    Retriever,
)

# ---------------------------------------------------------------------------
# 1. Enums
# ---------------------------------------------------------------------------


def test_intent_type_enum() -> None:
    assert IntentType.SEARCH == "search"
    assert IntentType.SPENDING_ANALYSIS == "spending_analysis"
    assert IntentType.COMPARISON == "comparison"
    assert IntentType.SUPPLIER_ANALYSIS == "supplier_analysis"
    assert IntentType.ORGANIZATION_ANALYSIS == "organization_analysis"
    assert IntentType.PRICE_ANALYSIS == "price_analysis"
    assert IntentType.SEMANTIC_SEARCH == "semantic_search"
    assert IntentType.TREND_ANALYSIS == "trend_analysis"
    assert IntentType.DETAIL_LOOKUP == "detail_lookup"
    assert IntentType.UNKNOWN == "unknown/out_of_scope"


def test_retrieval_strategy_enum() -> None:
    assert RetrievalStrategy.SQL == "sql"
    assert RetrievalStrategy.SEMANTIC == "semantic"
    assert RetrievalStrategy.HYBRID == "hybrid"
    assert RetrievalStrategy.DIRECT == "direct"


def test_message_role_enum() -> None:
    assert MessageRole.SYSTEM == "system"
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"
    assert MessageRole.TOOL == "tool"


def test_conversation_status_enum() -> None:
    assert ConversationStatus.ACTIVE == "active"
    assert ConversationStatus.ARCHIVED == "archived"
    assert ConversationStatus.CLOSED == "closed"


# ---------------------------------------------------------------------------
# 2. Source Model
# ---------------------------------------------------------------------------


def test_source_model() -> None:
    src = Source(
        id="721-12-LP24",
        source_type="tender",
        title="Licitación Adquisición Servidores",
        url="https://mercadopublico.cl/tender/721-12-LP24",
        snippet="Adquisición de equipamiento informático para el Hospital Regional.",
        score=0.95,
        metadata={"organismo": "Servicio de Salud Valparaíso", "monto_total": 45000000},
    )
    assert src.id == "721-12-LP24"
    assert src.source_type == "tender"
    assert src.score == 0.95
    assert src.metadata["organismo"] == "Servicio de Salud Valparaíso"

    # Source is frozen (immutable)
    with pytest.raises(ValidationError):
        src.title = "Nuevo Título"  # type: ignore[misc]

    # Serialization roundtrip
    dumped = src.model_dump()
    assert dumped["id"] == "721-12-LP24"
    reconstructed = Source.model_validate(dumped)
    assert reconstructed == src


# ---------------------------------------------------------------------------
# 3. QueryPlan Model
# ---------------------------------------------------------------------------


def test_query_plan_sql_strategy() -> None:
    plan = QueryPlan(
        intent=IntentType.SPENDING_ANALYSIS,
        retrieval_strategy=RetrievalStrategy.SQL,
        sql_query="SELECT comprador_nombre, SUM(monto_total_pesos) FROM marts.fct_ordenes_compra GROUP BY 1",
        filters={"year": 2024},
        parameters={"year": 2024},
        rationale="Análisis cuantitativo de gasto por organismo en el año 2024.",
    )
    assert plan.intent == IntentType.SPENDING_ANALYSIS
    assert plan.retrieval_strategy == RetrievalStrategy.SQL
    assert "SELECT" in (plan.sql_query or "")
    assert plan.semantic_query is None


def test_query_plan_semantic_strategy() -> None:
    plan = QueryPlan(
        intent=IntentType.SEMANTIC_SEARCH,
        retrieval_strategy=RetrievalStrategy.SEMANTIC,
        semantic_query="suministro de ambulancias de alta complejidad",
        filters={"region": "Metropolitana"},
        rationale="Búsqueda vectorial de especificaciones técnicas similares.",
    )
    assert plan.retrieval_strategy == RetrievalStrategy.SEMANTIC
    assert plan.sql_query is None
    assert plan.semantic_query == "suministro de ambulancias de alta complejidad"


def test_query_plan_hybrid_strategy() -> None:
    plan = QueryPlan(
        intent=IntentType.SEARCH,
        retrieval_strategy=RetrievalStrategy.HYBRID,
        sql_query="SELECT id FROM ods.licitaciones WHERE estado = 'Publicada'",
        semantic_query="software hospitalario",
        rationale="Filtro relacional por estado combinado con similitud semántica de texto.",
    )
    assert plan.retrieval_strategy == RetrievalStrategy.HYBRID
    assert plan.sql_query is not None
    assert plan.semantic_query is not None


# ---------------------------------------------------------------------------
# 4. RetrievalResult, Context, and GroundingResult Models
# ---------------------------------------------------------------------------


def test_retrieval_result_model() -> None:
    src = Source(
        id="OC-991",
        source_type="purchase_order",
        title="Orden de Compra 991",
        snippet="Compra de insumos",
    )
    res = RetrievalResult(
        strategy_used=RetrievalStrategy.SQL,
        items=[{"comprador": "Minsal", "total": 12000000}],
        sources=[src],
        sql_executed="SELECT ...",
        execution_time_ms=15.4,
        total_results=1,
    )
    assert res.strategy_used == RetrievalStrategy.SQL
    assert len(res.items) == 1
    assert len(res.sources) == 1
    assert res.execution_time_ms == 15.4


def test_context_model() -> None:
    src = Source(id="1", source_type="tender", title="Tender 1")
    ctx = Context(
        formatted_prompt_context="### Fuentes disponibles:\n- Tender 1: Licitación de prueba",
        sources=[src],
        structured_data=[{"clave": "valor"}],
        token_estimate=120,
    )
    assert "Tender 1" in ctx.formatted_prompt_context
    assert len(ctx.sources) == 1
    assert ctx.token_estimate == 120


def test_grounding_result_model() -> None:
    src = Source(id="doc-1", source_type="tender", title="Documento 1")
    grounding = GroundingResult(
        is_grounded=True,
        grounding_score=0.98,
        unsupported_claims=[],
        validated_sources=[src],
        rationale="Todas las afirmaciones cuantitativas coinciden con la tabla de ordenes de compra.",
    )
    assert grounding.is_grounded is True
    assert grounding.grounding_score == 0.98
    assert len(grounding.unsupported_claims) == 0

    ungrounded = GroundingResult(
        is_grounded=False,
        grounding_score=0.45,
        unsupported_claims=["Se afirmó un gasto de 500M pero el total fue de 50M."],
        validated_sources=[],
        rationale="Alucinación detectada en montos monetarios.",
    )
    assert ungrounded.is_grounded is False
    assert len(ungrounded.unsupported_claims) == 1


# ---------------------------------------------------------------------------
# 5. ChatMessage & ConversationSession Models
# ---------------------------------------------------------------------------


def test_chat_message_model() -> None:
    conv_id = uuid.uuid4()
    msg = ChatMessage(
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="¿Cuánto gastó el Ministerio de Salud en 2024?",
    )
    assert msg.conversation_id == conv_id
    assert msg.role == MessageRole.USER
    assert msg.content == "¿Cuánto gastó el Ministerio de Salud en 2024?"
    assert msg.tokens_input is None


def test_conversation_session_model() -> None:
    sess_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    session = ConversationSession(
        id=sess_id,
        user_id=user_id,
        title="Análisis Minsal 2024",
        status=ConversationStatus.ACTIVE,
        metadata={"client": "web_chat"},
        created_at=now,
        updated_at=now,
    )
    assert session.id == sess_id
    assert session.user_id == user_id
    assert session.status == ConversationStatus.ACTIVE
    assert session.title == "Análisis Minsal 2024"


# ---------------------------------------------------------------------------
# 6. Abstract Protocols Adherence (@runtime_checkable)
# ---------------------------------------------------------------------------


class DummyIntentDetector:
    async def detect_intent(
        self,
        query: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> tuple[IntentType, float]:
        return IntentType.SPENDING_ANALYSIS, 0.99


class DummyQueryPlanner:
    async def plan_query(
        self,
        query: str,
        intent: IntentType,
        conversation_history: list[ChatMessage] | None = None,
    ) -> QueryPlan:
        return QueryPlan(
            intent=intent,
            retrieval_strategy=RetrievalStrategy.SQL,
            sql_query="SELECT 1",
        )


class DummyRetriever:
    async def retrieve(self, plan: QueryPlan) -> RetrievalResult:
        return RetrievalResult(
            strategy_used=plan.retrieval_strategy,
            items=[],
            sources=[],
        )


class DummyContextBuilder:
    def build_context(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        max_tokens: int = 4000,
    ) -> Context:
        return Context(
            formatted_prompt_context="context",
            sources=[],
            token_estimate=10,
        )


class DummyLLMGateway:
    async def generate_response(
        self,
        user_query: str,
        context: Context,
        system_prompt: str | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> ChatMessage:
        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Respuesta simulada",
        )


class DummyGroundingValidator:
    async def validate(
        self,
        generated_answer: str,
        context: Context,
    ) -> GroundingResult:
        return GroundingResult(
            is_grounded=True,
            grounding_score=1.0,
        )


def test_protocols_runtime_checkable() -> None:
    assert isinstance(DummyIntentDetector(), IntentDetector)
    assert isinstance(DummyQueryPlanner(), QueryPlanner)
    assert isinstance(DummyRetriever(), Retriever)
    assert isinstance(DummyContextBuilder(), ContextBuilder)
    assert isinstance(DummyLLMGateway(), LLMGateway)
    assert isinstance(DummyGroundingValidator(), GroundingValidator)
