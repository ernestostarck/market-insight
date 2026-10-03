"""Data Quality evaluation service and score calculation (Fase 8.8).

Provides reproducible data quality scoring across ETL pipelines based on
deterministic rules (Chilean RUT validation, positive amounts, valid ISO dates,
required IDs, known categories, and duplicate detection).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.monitoring.metrics import record_data_quality_metrics

logger = logging.getLogger(__name__)

_RUT_REGEX = re.compile(r"^\d{7,8}-[0-9kK]$")

# Weight assigned to each violation type in score deduction
VIOLATION_WEIGHTS: dict[str, float] = {
    "missing_id": 15.0,
    "invalid_rut": 10.0,
    "invalid_date": 10.0,
    "invalid_amount": 10.0,
    "missing_supplier": 10.0,
    "unknown_category": 5.0,
    "duplicate_record": 5.0,
    "null_field": 5.0,
    # Rejected by ETL validation and quarantined: worst case for that record.
    "failed_validation": 50.0,
}


@dataclass(slots=True)
class QualityViolation:
    code: str
    message: str
    field: str | None = None
    weight: float = 5.0


def validate_rut(rut_str: Any) -> bool:
    """Validate Chilean RUT syntax and verification digit (DV) using modulo 11."""
    if not isinstance(rut_str, str):
        return False
    clean = rut_str.strip().replace(".", "").upper()
    if "-" in clean:
        parts = clean.split("-")
        if len(parts) != 2:
            return False
        num_str, dv = parts
    else:
        if len(clean) < 8 or len(clean) > 9:
            return False
        num_str, dv = clean[:-1], clean[-1]

    if not num_str.isdigit() or len(num_str) < 7 or len(num_str) > 8:
        return False
    if dv not in "0123456789K":
        return False

    reversed_digits = [int(d) for d in reversed(num_str)]
    factors = [2, 3, 4, 5, 6, 7]
    s = sum(d * factors[i % len(factors)] for i, d in enumerate(reversed_digits))
    remainder = 11 - (s % 11)
    if remainder == 11:
        expected_dv = "0"
    elif remainder == 10:
        expected_dv = "K"
    else:
        expected_dv = str(remainder)

    return dv == expected_dv


def validate_iso_date(date_val: Any) -> bool:
    """Validate date is a datetime object or valid ISO-8601 string."""
    if isinstance(date_val, datetime):
        return True
    if not isinstance(date_val, str):
        return False
    try:
        datetime.fromisoformat(date_val.strip())
        return True
    except (ValueError, TypeError):
        return False


def validate_non_negative_amount(amount_val: Any) -> bool:
    """Validate amount is a non-negative float or int (or numeric string)."""
    if amount_val is None:
        return False
    if isinstance(amount_val, bool):
        return False
    if isinstance(amount_val, (int, float)):
        return amount_val >= 0
    if isinstance(amount_val, str):
        try:
            val = float(amount_val.strip())
            return val >= 0
        except (ValueError, TypeError):
            return False
    return False


def evaluate_record(record: dict[str, Any]) -> list[QualityViolation]:
    """Evaluate quality rules on a single normalized record dictionary."""
    violations: list[QualityViolation] = []

    # 1. Missing mandatory tender ID
    tender_id = record.get("codigo") or record.get("id") or record.get("codigo_externo")
    if not tender_id or (isinstance(tender_id, str) and not tender_id.strip()):
        violations.append(
            QualityViolation(
                code="missing_id",
                message="Record is missing a mandatory identifier (codigo/id).",
                field="codigo",
                weight=VIOLATION_WEIGHTS["missing_id"],
            )
        )

    # 2. RUT validation
    for rut_field in ("rut_proveedor", "rut_comprador", "rut"):
        if rut_field in record and record[rut_field] is not None and not validate_rut(record[rut_field]):
            violations.append(
                QualityViolation(
                    code="invalid_rut",
                    message=f"Field '{rut_field}' is not a valid Chilean RUT.",
                    field=rut_field,
                    weight=VIOLATION_WEIGHTS["invalid_rut"],
                )
            )

    # 3. Date validation
    for date_field in ("fecha_creacion", "fecha_cierre", "created_at", "updated_at"):
        if date_field in record and record[date_field] is not None and not validate_iso_date(record[date_field]):
            violations.append(
                QualityViolation(
                    code="invalid_date",
                    message=f"Field '{date_field}' contains an invalid date format.",
                    field=date_field,
                    weight=VIOLATION_WEIGHTS["invalid_date"],
                )
            )

    # 4. Amount validation
    for amount_field in ("monto_total", "monto", "total", "precio"):
        if amount_field in record and record[amount_field] is not None and not validate_non_negative_amount(record[amount_field]):
            violations.append(
                QualityViolation(
                    code="invalid_amount",
                    message=f"Field '{amount_field}' must be a non-negative number.",
                    field=amount_field,
                    weight=VIOLATION_WEIGHTS["invalid_amount"],
                )
            )

    # 5. Missing supplier
    if "proveedor" in record and not record.get("proveedor") and not record.get("rut_proveedor"):
        violations.append(
            QualityViolation(
                code="missing_supplier",
                message="Awarded record has no associated supplier information.",
                field="proveedor",
                weight=VIOLATION_WEIGHTS["missing_supplier"],
            )
        )

    return violations


def compute_data_quality_score(
    violations: list[QualityViolation],
    total_records: int,
    duplicates: int = 0,
) -> float:
    """Compute a reproducible Data Quality Score between 0.0 and 100.0.

    Formula:
    Base = 100.0
    Weighted penalties are normalized across the evaluated batch size.
    Each record can incur deductions up to its maximum potential weight.
    """
    if total_records <= 0:
        return 100.0

    total_penalty = sum(v.weight for v in violations)
    total_penalty += duplicates * VIOLATION_WEIGHTS["duplicate_record"]

    # Maximum potential penalty budget per record is ~50 points
    max_budget = total_records * 50.0
    score = 100.0 * (1.0 - (total_penalty / max_budget))
    return round(max(0.0, min(100.0, score)), 2)


def evaluate_batch(
    pipeline: str,
    records: list[dict[str, Any]],
    duplicates: int = 0,
    invalid_count: int = 0,
) -> float:
    """Evaluate a batch of records, update Prometheus metrics, and return score.

    ``invalid_count`` is the number of records ETL validation rejected before they
    could be evaluated here; they weigh as the worst case so a batch that is mostly
    quarantined cannot score as healthy.
    """
    all_violations: list[QualityViolation] = []
    invalid_counts: dict[str, int] = {}

    for rec in records:
        v_list = evaluate_record(rec)
        all_violations.extend(v_list)
        for v in v_list:
            invalid_counts[v.code] = invalid_counts.get(v.code, 0) + 1

    if invalid_count > 0:
        invalid_counts["failed_validation"] = invalid_count
        all_violations.extend(
            QualityViolation(
                code="failed_validation",
                message="Record rejected by ETL validation and quarantined.",
                weight=VIOLATION_WEIGHTS["failed_validation"],
            )
            for _ in range(invalid_count)
        )

    score = compute_data_quality_score(
        violations=all_violations,
        total_records=len(records) + invalid_count,
        duplicates=duplicates,
    )

    record_data_quality_metrics(
        pipeline=pipeline,
        score=score,
        duplicates=duplicates,
        invalid_counts=invalid_counts,
    )

    return score
