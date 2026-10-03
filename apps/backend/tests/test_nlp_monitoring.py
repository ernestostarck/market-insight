from __future__ import annotations

import pytest

from app.nlp.observability.metrics import (
    NLP_CATEGORY_DISTRIBUTION_TOTAL,
    NLP_CLASSIFICATIONS_TOTAL,
    NLP_DATA_DRIFT_KL_DIVERGENCE,
    NLP_DOCUMENTS_PROCESSED_TOTAL,
    NLP_EMBEDDING_FAILURES_TOTAL,
    NLP_LOW_CONFIDENCE_TOTAL,
    record_nlp_classification,
    record_nlp_document,
    record_nlp_embedding_failure,
)


def test_record_nlp_document() -> None:
    initial_val = NLP_DOCUMENTS_PROCESSED_TOTAL.labels(
        stage="classification", status="success"
    )._value.get()

    record_nlp_document(
        stage="classification",
        status="success",
        duration_seconds=0.15,
    )

    new_val = NLP_DOCUMENTS_PROCESSED_TOTAL.labels(
        stage="classification", status="success"
    )._value.get()
    assert new_val == initial_val + 1


def test_record_nlp_classification_high_confidence() -> None:
    initial_classifications = NLP_CLASSIFICATIONS_TOTAL.labels(
        category_code="SALUD", method="hybrid"
    )._value.get()
    initial_low_conf = NLP_LOW_CONFIDENCE_TOTAL.labels(
        method="hybrid"
    )._value.get()

    record_nlp_classification(
        category_code="SALUD",
        method="hybrid",
        confidence=0.92,
    )

    assert (
        NLP_CLASSIFICATIONS_TOTAL.labels(
            category_code="SALUD", method="hybrid"
        )._value.get()
        == initial_classifications + 1
    )
    assert (
        NLP_CATEGORY_DISTRIBUTION_TOTAL.labels(
            category_code="SALUD"
        )._value.get()
        >= 1
    )
    # Since confidence (0.92) >= 0.70 threshold, low confidence total should not increment
    assert (
        NLP_LOW_CONFIDENCE_TOTAL.labels(
            method="hybrid"
        )._value.get()
        == initial_low_conf
    )


def test_record_nlp_classification_low_confidence() -> None:
    initial_low_conf = NLP_LOW_CONFIDENCE_TOTAL.labels(
        method="keyword"
    )._value.get()

    record_nlp_classification(
        category_code="CONSTRUCCION",
        method="keyword",
        confidence=0.45,
    )

    assert (
        NLP_LOW_CONFIDENCE_TOTAL.labels(
            method="keyword"
        )._value.get()
        == initial_low_conf + 1
    )


def test_record_nlp_embedding_failure() -> None:
    initial_failures = NLP_EMBEDDING_FAILURES_TOTAL.labels(
        model="text-embedding-3-small"
    )._value.get()

    record_nlp_embedding_failure(
        model="text-embedding-3-small"
    )

    assert (
        NLP_EMBEDDING_FAILURES_TOTAL.labels(
            model="text-embedding-3-small"
        )._value.get()
        == initial_failures + 1
    )


def test_nlp_data_drift_metric() -> None:
    NLP_DATA_DRIFT_KL_DIVERGENCE.set(0.125)
    assert NLP_DATA_DRIFT_KL_DIVERGENCE._value.get() == pytest.approx(0.125)
