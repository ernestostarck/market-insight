"""Observability and monitoring package for NLP pipeline (Fase 6.24)."""

from app.nlp.observability.drift import DataDriftDetector, DriftReport
from app.nlp.observability.metrics import (
    NLP_CATEGORY_DISTRIBUTION_TOTAL,
    NLP_CONFIDENCE_SCORE,
    NLP_DATA_DRIFT_KL_DIVERGENCE,
    NLP_ERRORS_TOTAL,
    NLP_HUMAN_REVIEWS_TOTAL,
    NLP_PROCESSING_DURATION_SECONDS,
    NLP_TENDERS_PROCESSED_TOTAL,
)

__all__ = [
    "NLP_CATEGORY_DISTRIBUTION_TOTAL",
    "NLP_CONFIDENCE_SCORE",
    "NLP_DATA_DRIFT_KL_DIVERGENCE",
    "NLP_ERRORS_TOTAL",
    "NLP_HUMAN_REVIEWS_TOTAL",
    "NLP_PROCESSING_DURATION_SECONDS",
    "NLP_TENDERS_PROCESSED_TOTAL",
    "DataDriftDetector",
    "DriftReport",
]
