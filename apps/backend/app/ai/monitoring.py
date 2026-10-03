"""Prometheus Observability instrumentation for MercadoInsight Conversational RAG (Fase 9.23).

Registers custom Prometheus Counters, Histograms and Gauges for:
1. End-to-end RAG turn latencies (retrieval, generation, verification)
2. Token usage and USD cost tracking
3. Grounding validation scores and hallucination incidents
4. Safety guardrail interventions (Injection & Scope)
5. User feedback metrics (Thumbs Up / Down)
"""

from __future__ import annotations

import logging

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# 1. Requests & Latencies
AI_RAG_REQUESTS_TOTAL = Counter(
    "ai_rag_requests_total",
    "Total RAG requests processed by intent, retrieval strategy and outcome status.",
    ["intent", "retrieval_strategy", "status"],
)

AI_RAG_LATENCY_SECONDS = Histogram(
    "ai_rag_latency_seconds",
    "Latency of conversational RAG turns in seconds broken down by pipeline stage.",
    ["stage"],
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
)

# 2. Token Usage & Cost (Fase 9.24)
AI_RAG_TOKENS_TOTAL = Counter(
    "ai_rag_tokens_total",
    "Total tokens consumed by AI inference models.",
    ["type", "model"],  # type: input | output
)

AI_RAG_COST_USD_TOTAL = Counter(
    "ai_rag_cost_usd_total",
    "Estimated total inference cost in USD broken down by model and intent.",
    ["model", "intent"],
)

AI_COSTLY_QUERIES_TOTAL = Counter(
    "ai_costly_queries_total",
    "Total queries flagged as abnormally costly or exceeding token thresholds.",
    ["model"],
)

# 3. Quality & Grounding
AI_GROUNDING_SCORE = Histogram(
    "ai_grounding_score",
    "Distribution of factual grounding scores produced by GroundingValidator.",
    ["grounded"],  # "true" | "false"
    buckets=(0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0),
)

# 4. Guardrails & Safety
AI_GUARDRAIL_BLOCKS_TOTAL = Counter(
    "ai_guardrail_blocks_total",
    "Total requests blocked by safety guardrails.",
    ["layer"],  # injection | scope | sql | data
)

# 5. User Feedback (Fase 9.21)
AI_FEEDBACK_TOTAL = Counter(
    "ai_feedback_total",
    "Total user feedback recorded.",
    ["rating", "reason"],  # rating: "positive" | "negative"
)


def record_rag_turn_metrics(
    intent: str,
    retrieval_strategy: str,
    latency_ms: float,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    model: str,
    grounding_score: float,
    is_grounded: bool,
    status: str = "success",
) -> None:
    """Convenience helper to record all telemetry points for a completed RAG turn."""
    try:
        AI_RAG_REQUESTS_TOTAL.labels(
            intent=intent,
            retrieval_strategy=retrieval_strategy,
            status=status,
        ).inc()

        AI_RAG_LATENCY_SECONDS.labels(stage="total").observe(latency_ms / 1000.0)

        if tokens_input > 0:
            AI_RAG_TOKENS_TOTAL.labels(type="input", model=model).inc(tokens_input)
        if tokens_output > 0:
            AI_RAG_TOKENS_TOTAL.labels(type="output", model=model).inc(tokens_output)

        if cost_usd > 0.0:
            AI_RAG_COST_USD_TOTAL.labels(model=model, intent=intent).inc(cost_usd)

        AI_GROUNDING_SCORE.labels(grounded="true" if is_grounded else "false").observe(
            max(0.0, min(1.0, grounding_score))
        )
    except (ValueError, TypeError, KeyError) as e:
        logger.debug("Failed to record RAG Prometheus metrics: %s", e)
