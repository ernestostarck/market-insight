"""Prometheus metrics for the NLP pipeline and AI capabilities (Fase 6.24 & Fase 8.9)."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# 1. Total processed documents by stage and outcome status (8.9.2)
NLP_DOCUMENTS_PROCESSED_TOTAL = Counter(
    "nlp_documents_processed_total",
    "Total documents processed across NLP stages.",
    ["stage", "status"],
)

# 2. Total classifications by category and method (8.9.3)
NLP_CLASSIFICATIONS_TOTAL = Counter(
    "nlp_classifications_total",
    "Total classifications performed by category and winning method.",
    ["category_code", "method"],
)

# 3. Documents classified with low confidence (< 0.70) (8.9.4 & 8.9.7)
NLP_LOW_CONFIDENCE_TOTAL = Counter(
    "nlp_low_confidence_total",
    "Total documents classified with low confidence score (< 0.70).",
    ["method"],
)

# 4. Stage latency distributions in seconds (8.9.5 & 8.9.8)
NLP_PROCESSING_DURATION_SECONDS = Histogram(
    "nlp_processing_duration_seconds",
    "Duration of NLP processing stages in seconds.",
    ["stage"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# 5. Total embedding generation failures (8.9.6)
NLP_EMBEDDING_FAILURES_TOTAL = Counter(
    "nlp_embedding_failures_total",
    "Total failures encountered during vector embedding generation.",
    ["model"],
)

# 6. Total error counts by stage and error code (8.9.10)
NLP_ERRORS_TOTAL = Counter(
    "nlp_errors_total",
    "Total errors encountered in the NLP pipeline.",
    ["stage", "error_code"],
)

# 7. Classification confidence score distribution
NLP_CONFIDENCE_SCORE = Histogram(
    "nlp_confidence_score",
    "Distribution of hybrid classification confidence scores.",
    ["winning_method"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

# 8. Category distribution count (8.9.12)
NLP_CATEGORY_DISTRIBUTION_TOTAL = Counter(
    "nlp_category_distribution_total",
    "Count of tenders classified into each category.",
    ["category_code"],
)

# 9. Human review actions (accept, modify)
NLP_HUMAN_REVIEWS_TOTAL = Counter(
    "nlp_human_reviews_total",
    "Total Human-in-the-Loop review actions executed.",
    ["action"],
)

# 10. Data distribution drift metric (KL divergence) (8.9.13)
NLP_DATA_DRIFT_KL_DIVERGENCE = Gauge(
    "nlp_data_drift_kl_divergence",
    "Kullback-Leibler divergence measuring semantic/categorical distribution drift against baseline.",
)

# Backward-compatibility aliases for earlier phase tests
NLP_TENDERS_PROCESSED_TOTAL = NLP_DOCUMENTS_PROCESSED_TOTAL


def record_nlp_document(
    stage: str,
    status: str = "success",
    duration_seconds: float | None = None,
) -> None:
    """Record an NLP document processed through a pipeline stage."""
    NLP_DOCUMENTS_PROCESSED_TOTAL.labels(stage=stage, status=status).inc()
    if duration_seconds is not None:
        NLP_PROCESSING_DURATION_SECONDS.labels(stage=stage).observe(max(duration_seconds, 0.0))


def record_nlp_classification(
    category_code: str,
    method: str,
    confidence: float,
) -> None:
    """Record a tender classification, category distribution, and low confidence flag."""
    NLP_CLASSIFICATIONS_TOTAL.labels(category_code=category_code, method=method).inc()
    NLP_CATEGORY_DISTRIBUTION_TOTAL.labels(category_code=category_code).inc()
    NLP_CONFIDENCE_SCORE.labels(winning_method=method).observe(confidence)
    if confidence < 0.70:
        NLP_LOW_CONFIDENCE_TOTAL.labels(method=method).inc()


def record_nlp_embedding_failure(model: str = "text-embedding-3-small") -> None:
    """Record an embedding model failure."""
    NLP_EMBEDDING_FAILURES_TOTAL.labels(model=model).inc()
    NLP_ERRORS_TOTAL.labels(stage="embeddings", error_code="embedding_failure").inc()
