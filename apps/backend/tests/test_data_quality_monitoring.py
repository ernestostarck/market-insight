from __future__ import annotations

import pytest

from app.monitoring.data_quality import (
    QualityViolation,
    compute_data_quality_score,
    evaluate_batch,
    evaluate_record,
    validate_iso_date,
    validate_non_negative_amount,
    validate_rut,
)
from app.monitoring.metrics import (
    DATA_QUALITY_SCORE,
    DUPLICATE_RECORDS_TOTAL,
    INVALID_RECORDS_TOTAL,
)


def test_validate_rut_valid_formats() -> None:
    # Valid Chilean RUTs (both standard and with K digit)
    assert validate_rut("11.111.111-1") is True
    assert validate_rut("11111111-1") is True
    assert validate_rut("111111111") is True
    assert validate_rut("11.111.112-K") is True
    assert validate_rut("11111112-k") is True


def test_validate_rut_invalid_formats() -> None:
    assert validate_rut(None) is False
    assert validate_rut("") is False
    assert validate_rut("123") is False
    # Wrong check digit (11.111.111-2 should fail)
    assert validate_rut("11.111.111-2") is False
    assert validate_rut("abc-1") is False


def test_validate_iso_date() -> None:
    assert validate_iso_date("2026-09-20") is True
    assert validate_iso_date("2026-09-20T12:00:00Z") is True
    assert validate_iso_date("2026-09-20T12:00:00+00:00") is True
    assert validate_iso_date("invalid-date") is False
    assert validate_iso_date(None) is False
    assert validate_iso_date("") is False


def test_validate_non_negative_amount() -> None:
    assert validate_non_negative_amount(100.0) is True
    assert validate_non_negative_amount(0) is True
    assert validate_non_negative_amount("5000") is True
    assert validate_non_negative_amount(-10) is False
    assert validate_non_negative_amount("-50.5") is False
    assert validate_non_negative_amount("abc") is False
    assert validate_non_negative_amount(None) is False


def test_evaluate_record_clean() -> None:
    clean_record = {
        "codigo": "1234-56-LP26",
        "rut_comprador": "11.111.111-1",
        "fecha_creacion": "2026-09-20T10:00:00Z",
        "monto_total": 1500000.0,
        "rut_proveedor": "11.111.112-K",
        "proveedor": "Proveedor Ejemplo S.A.",
    }
    violations = evaluate_record(clean_record)
    assert len(violations) == 0


def test_evaluate_record_with_violations() -> None:
    invalid_record = {
        "codigo": "",
        "rut_comprador": "invalid-rut",
        "fecha_creacion": "bad-date",
        "monto_total": -500,
        "proveedor": "",
        "rut_proveedor": None,
    }
    violations = evaluate_record(invalid_record)
    violation_codes = {v.code for v in violations}

    assert "missing_id" in violation_codes
    assert "invalid_rut" in violation_codes
    assert "invalid_date" in violation_codes
    assert "invalid_amount" in violation_codes
    assert "missing_supplier" in violation_codes


def test_compute_data_quality_score() -> None:
    # 0 violations -> 100.0
    assert compute_data_quality_score([], 10) == 100.0
    assert compute_data_quality_score([], 0) == 100.0

    # 10 records with 1 missing_id violation (weight 15)
    # max_budget = 10 * 50 = 500.0
    # penalty = 15
    # score = 100 * (1 - 15/500) = 97.0
    violations = [QualityViolation(code="missing_id", message="missing", weight=15.0)]
    score = compute_data_quality_score(violations, total_records=10)
    assert score == 97.0

    # Severe violations clamped to 0.0
    heavy_violations = [
        QualityViolation(code="missing_id", message="missing", weight=500.0)
    ]
    clamped_score = compute_data_quality_score(heavy_violations, total_records=1)
    assert clamped_score == 0.0


def test_evaluate_batch_and_record_metrics() -> None:
    batch = [
        {
            "codigo": "T001",
            "rut_comprador": "11.111.111-1",
            "fecha_creacion": "2026-09-20",
            "monto_total": 1000,
            "rut_proveedor": "11.111.112-K",
            "proveedor": "Proveedor A",
        },
        {
            "codigo": "T002",
            "rut_comprador": "invalid-rut",
            "fecha_creacion": "2026-09-20",
            "monto_total": 2000,
            "rut_proveedor": "11.111.111-1",
            "proveedor": "Proveedor B",
        },
    ]

    score = evaluate_batch("licitaciones", batch, duplicates=1)
    assert score < 100.0

    # Verify Prometheus metrics updated
    assert DATA_QUALITY_SCORE.labels(pipeline="licitaciones")._value.get() == pytest.approx(score)
    assert DUPLICATE_RECORDS_TOTAL.labels(pipeline="licitaciones")._value.get() >= 1
    assert INVALID_RECORDS_TOTAL.labels(pipeline="licitaciones", reason="invalid_rut")._value.get() >= 1
