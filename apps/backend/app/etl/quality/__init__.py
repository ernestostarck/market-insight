"""Data quality layer for the ETL pipeline (Fase 3.10).

Exposes:

* :func:`QualityReporter` — the protocol the pipeline expects for the
  ``quality_reporter`` hook.
* :class:`DataQualityReporter` — a concrete reporter that computes and records
  :class:`QualityMetrics` for each run.
* Quality metric helpers (:func:`quality_rate`, :func:`metrics_from_etl`).
* Domain quality rules (:func:`rule_rut`, :func:`rule_positive_number`, ...)
  and the aggregator :func:`evaluate_rules`.
"""

from app.etl.quality.base import QualityReporter
from app.etl.quality.metrics import (
    QualityMetrics,
    metrics_from_etl,
    quality_rate,
)
from app.etl.quality.reporter import DataQualityReporter
from app.etl.quality.rules import (
    QualityReport,
    QualityViolation,
    evaluate_rules,
    full_payload_rules,
    rule_allowlist,
    rule_iso_datetime,
    rule_non_negative_number,
    rule_positive_number,
    rule_reasonable_amount,
    rule_required,
    rule_rut,
)

__all__ = [
    "QualityReporter",
    "DataQualityReporter",
    "QualityMetrics",
    "quality_rate",
    "metrics_from_etl",
    "QualityReport",
    "QualityViolation",
    "evaluate_rules",
    "full_payload_rules",
    "rule_required",
    "rule_non_negative_number",
    "rule_positive_number",
    "rule_iso_datetime",
    "rule_reasonable_amount",
    "rule_rut",
    "rule_allowlist",
]
