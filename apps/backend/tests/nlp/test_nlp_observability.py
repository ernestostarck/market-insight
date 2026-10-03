"""Unit tests for NLP Observability, Prometheus metrics, and Data Drift (Fase 6.24)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.metrics import render_metrics
from app.main import app
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


def test_data_drift_detector_no_drift() -> None:
    detector = DataDriftDetector(drift_threshold=0.20)

    # Identical distributions
    baseline = {"SALUD": 100, "TECNOLOGIA": 50, "CONSTRUCCION": 50}
    observed = {"SALUD": 100, "TECNOLOGIA": 50, "CONSTRUCCION": 50}

    report = detector.compute_drift(observed, baseline)
    assert isinstance(report, DriftReport)
    assert not report.drift_detected
    assert report.kl_divergence < 0.01


def test_data_drift_detector_detects_significant_drift() -> None:
    detector = DataDriftDetector(drift_threshold=0.20)

    # Significant shift: baseline was mostly SALUD, observed is mostly TECNOLOGIA
    baseline = {"SALUD": 800, "TECNOLOGIA": 100, "CONSTRUCCION": 100}
    observed = {"SALUD": 50, "TECNOLOGIA": 850, "CONSTRUCCION": 100}

    report = detector.compute_drift(observed, baseline)
    assert report.drift_detected
    assert report.kl_divergence > 0.20
    assert report.largest_shift_category in ("SALUD", "TECNOLOGIA")


def test_nlp_prometheus_metrics_instrumentation_and_render() -> None:
    # 1. Exercise counters, histograms, and gauges
    NLP_TENDERS_PROCESSED_TOTAL.labels(stage="classification", status="succeeded").inc()
    NLP_PROCESSING_DURATION_SECONDS.labels(stage="classification").observe(0.42)
    NLP_ERRORS_TOTAL.labels(stage="ner", error_code="timeout").inc()
    NLP_CONFIDENCE_SCORE.labels(winning_method="hybrid").observe(0.91)
    NLP_CATEGORY_DISTRIBUTION_TOTAL.labels(category_code="SALUD").inc()
    NLP_HUMAN_REVIEWS_TOTAL.labels(action="accepted").inc()
    NLP_DATA_DRIFT_KL_DIVERGENCE.set(0.1234)

    # 2. Render metrics via core renderer
    content, content_type = render_metrics()
    text = content.decode("utf-8")

    assert "nlp_documents_processed_total" in text
    assert "nlp_processing_duration_seconds" in text
    assert "nlp_errors_total" in text
    assert "nlp_confidence_score" in text
    assert "nlp_category_distribution_total" in text
    assert "nlp_human_reviews_total" in text
    assert "nlp_data_drift_kl_divergence" in text


def test_fastapi_metrics_endpoint_includes_nlp_metrics() -> None:
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "nlp_" in response.text
