"""AI Cost and Token Usage Tracker (Fase 9.24).

Tracks and aggregates token consumption and monetary inference expenses
across queries, conversations, users, models and intent categories.
Provides anomaly detection for costly queries and budgetary thresholds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.monitoring import (
    AI_COSTLY_QUERIES_TOTAL,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelPricing:
    """Pricing rates per 1,000,000 tokens in USD."""

    input_per_million: float
    output_per_million: float
    provider: str


# Canonical price table for LLM inference engines (USD per 1M tokens)
MODEL_PRICING_CATALOG: dict[str, ModelPricing] = {
    "gemini-2.5-flash": ModelPricing(input_per_million=0.075, output_per_million=0.30, provider="google"),
    "gemini-1.5-flash": ModelPricing(input_per_million=0.075, output_per_million=0.30, provider="google"),
    "gemini-1.5-pro": ModelPricing(input_per_million=1.25, output_per_million=5.00, provider="google"),
    "gpt-4o-mini": ModelPricing(input_per_million=0.15, output_per_million=0.60, provider="openai"),
    "local-deterministic": ModelPricing(input_per_million=0.0, output_per_million=0.0, provider="local"),
    "default": ModelPricing(input_per_million=0.10, output_per_million=0.40, provider="generic"),
}

# Safety thresholds for anomaly detection
DEFAULT_MAX_TOKENS_PER_QUERY = 8000
DEFAULT_MAX_COST_USD_PER_QUERY = 0.05


class QueryCostRecord(BaseModel):
    """Detailed record of cost and token expenditure for a single turn."""

    query_id: str
    model: str
    provider: str
    intent: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    is_anomalous: bool = False
    user_id: str | None = None
    conversation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CostTracker:
    """Manages AI inference budget, cost tracking, and token aggregation."""

    def __init__(
        self,
        pricing_catalog: dict[str, ModelPricing] | None = None,
        max_tokens_per_query: int = DEFAULT_MAX_TOKENS_PER_QUERY,
        max_cost_per_query: float = DEFAULT_MAX_COST_USD_PER_QUERY,
    ) -> None:
        self.pricing = pricing_catalog or dict(MODEL_PRICING_CATALOG)
        self.max_tokens_per_query = max_tokens_per_query
        self.max_cost_per_query = max_cost_per_query
        # In-memory accumulator for instant analytics (can be backed by DB/Redis)
        self._records: list[QueryCostRecord] = []

    def get_pricing(self, model: str) -> ModelPricing:
        """Resolve pricing for a model name or fallback to default."""
        m_lower = model.lower()
        for key, p in self.pricing.items():
            if key in m_lower:
                return p
        return self.pricing.get("default", ModelPricing(0.10, 0.40, "generic"))

    def calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate estimated cost in USD for the given token quantities."""
        pricing = self.get_pricing(model)
        cost_in = (tokens_input / 1_000_000.0) * pricing.input_per_million
        cost_out = (tokens_output / 1_000_000.0) * pricing.output_per_million
        return round(cost_in + cost_out, 6)

    def record_query_cost(
        self,
        query_id: str,
        model: str,
        intent: str,
        tokens_input: int,
        tokens_output: int,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> QueryCostRecord:
        """Calculate and store a query cost transaction, updating Prometheus metrics."""
        pricing = self.get_pricing(model)
        tokens_total = tokens_input + tokens_output
        cost_usd = self.calculate_cost(model, tokens_input, tokens_output)

        is_anomalous = (tokens_total > self.max_tokens_per_query) or (cost_usd > self.max_cost_per_query)

        record = QueryCostRecord(
            query_id=query_id,
            model=model,
            provider=pricing.provider,
            intent=intent,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
            cost_usd=cost_usd,
            is_anomalous=is_anomalous,
            user_id=str(user_id) if user_id else None,
            conversation_id=str(conversation_id) if conversation_id else None,
        )

        self._records.append(record)

        # Telemetry
        if is_anomalous:
            AI_COSTLY_QUERIES_TOTAL.labels(model=model).inc()
            logger.warning(
                "Anomalous query cost detected: id=%s, tokens=%d, cost=$%.4f, model=%s",
                query_id,
                tokens_total,
                cost_usd,
                model,
            )

        return record

    def get_summary(
        self,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Aggregate cost statistics with optional user or conversation filters."""
        filtered = self._records
        if user_id:
            filtered = [r for r in filtered if r.user_id == str(user_id)]
        if conversation_id:
            filtered = [r for r in filtered if r.conversation_id == str(conversation_id)]

        total_cost = sum(r.cost_usd for r in filtered)
        total_in = sum(r.tokens_input for r in filtered)
        total_out = sum(r.tokens_output for r in filtered)

        by_model: dict[str, dict[str, Any]] = {}
        by_intent: dict[str, float] = {}

        for r in filtered:
            by_intent[r.intent] = round(by_intent.get(r.intent, 0.0) + r.cost_usd, 6)
            if r.model not in by_model:
                by_model[r.model] = {
                    "provider": r.provider,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "cost_usd": 0.0,
                    "queries": 0,
                }
            by_model[r.model]["tokens_input"] += r.tokens_input
            by_model[r.model]["tokens_output"] += r.tokens_output
            by_model[r.model]["cost_usd"] = round(by_model[r.model]["cost_usd"] + r.cost_usd, 6)
            by_model[r.model]["queries"] += 1

        return {
            "total_cost_usd": round(total_cost, 6),
            "total_tokens_input": total_in,
            "total_tokens_output": total_out,
            "total_tokens": total_in + total_out,
            "queries_count": len(filtered),
            "by_model": by_model,
            "by_intent": by_intent,
        }


_global_cost_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Singleton getter for CostTracker."""
    global _global_cost_tracker
    if _global_cost_tracker is None:
        _global_cost_tracker = CostTracker()
    return _global_cost_tracker
