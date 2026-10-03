"""Abstract interfaces and protocols for MercadoInsight AI components (Fase 9.1).

Enforces strict separation of concerns and provider independence across
Intent Detection, Query Planning, Retrieval, Context Construction, Generation, and Grounding.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.ai.contracts import (
    ChatMessage,
    Context,
    GroundingResult,
    IntentType,
    QueryPlan,
    RetrievalResult,
)


@runtime_checkable
class IntentDetector(Protocol):
    """Protocol for classifying the intent of a user query."""

    async def detect_intent(
        self,
        query: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> tuple[IntentType, float]:
        """Detect intent and return (IntentType, confidence_score)."""
        ...


@runtime_checkable
class QueryPlanner(Protocol):
    """Protocol for formulating a deterministic retrieval execution plan."""

    async def plan_query(
        self,
        query: str,
        intent: IntentType,
        conversation_history: list[ChatMessage] | None = None,
    ) -> QueryPlan:
        """Formulate a QueryPlan specifying strategy, SQL, semantic queries, and filters."""
        ...


@runtime_checkable
class Retriever(Protocol):
    """Protocol for executing evidence retrieval across SQL and vector databases."""

    async def retrieve(self, plan: QueryPlan) -> RetrievalResult:
        """Execute the query plan and return structured items and sources."""
        ...


@runtime_checkable
class ContextBuilder(Protocol):
    """Protocol for assembling retrieved evidence into a prompt-ready context."""

    def build_context(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        max_tokens: int = 4000,
    ) -> Context:
        """Compile items and sources into a structured Context."""
        ...


@runtime_checkable
class LLMGateway(Protocol):
    """Protocol for communicating with language models in a provider-agnostic manner."""

    async def generate_response(
        self,
        user_query: str,
        context: Context,
        system_prompt: str | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> ChatMessage:
        """Generate an assistant message grounded in the provided context."""
        ...


@runtime_checkable
class GroundingValidator(Protocol):
    """Protocol for validating that the generated answer is strictly grounded in evidence."""

    async def validate(
        self,
        generated_answer: str,
        context: Context,
    ) -> GroundingResult:
        """Verify that claims in the answer are substantiated by the context sources."""
        ...
