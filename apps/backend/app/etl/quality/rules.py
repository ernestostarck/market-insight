"""Data quality rules for the ETL pipeline (Fase 3.10).

Quality rules are small, domain-aware predicate checks applied to a normalized
payload (the ``dict`` produced by the validation/normalization step). Each rule
returns a list of :class:`QualityViolation` objects describing any problems
found, or an empty list when the payload is compliant.

Unlike schema validation (which rejects raw payloads that cannot be parsed),
quality rules are *heuristic*: they flag suspicious-but-parseable values and
feed the quality metrics rather than quarantine a record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

_RUT_PATTERN = re.compile(r"^\d{7,8}-[0-9K]$")


@dataclass(slots=True)
class QualityViolation:
    """A single quality problem found for a record."""

    #: Stable rule identifier, e.g. ``invalid_rut``.
    code: str
    #: Human-readable description of the problem.
    message: str
    #: Payload field that triggered the violation (may be ``None``).
    field: str | None = None
    #: Severity: ``info``, ``warning`` or ``error``.
    severity: str = "warning"
    #: Number of times this violation appeared (for aggregation).
    count: int = 1


@dataclass(slots=True)
class QualityReport:
    """Aggregated violations for a payload."""

    violations: list[QualityViolation] = field(default_factory=list)
    #: Total checks that passed across all evaluated rules.
    passed_checks: int = 0

    @property
    def is_clean(self) -> bool:
        return not self.violations

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    def add(self, violation: QualityViolation) -> None:
        self.violations.append(violation)


# A rule is a callable ``(payload) -> list[QualityViolation]``.
QualityRule = Callable[[dict[str, Any]], list[QualityViolation]]


# ------------------------------------------------------------------------- #
# Built-in rules
# ------------------------------------------------------------------------- #
def rule_required(payload: dict[str, Any], field: str) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        return [
            QualityViolation(
                code="missing_value",
                message=f"Field '{field}' is missing or empty.",
                field=field,
                severity="error",
            )
        ]
    return []


def rule_non_negative_number(
    payload: dict[str, Any], field: str
) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None:
        return []
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [
            QualityViolation(
                code="invalid_numeric_type",
                message=f"Field '{field}' must be a number, got {type(value).__name__}.",
                field=field,
                severity="error",
            )
        ]
    if value < 0:
        return [
            QualityViolation(
                code="negative_number",
                message=f"Field '{field}' must not be negative.",
                field=field,
                severity="error",
            )
        ]
    return []


def rule_positive_number(payload: dict[str, Any], field: str) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None:
        return []
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [
            QualityViolation(
                code="invalid_numeric_type",
                message=f"Field '{field}' must be a number.",
                field=field,
                severity="error",
            )
        ]
    if value <= 0:
        return [
            QualityViolation(
                code="non_positive_number",
                message=f"Field '{field}' must be greater than zero.",
                field=field,
                severity="error",
            )
        ]
    return []


def rule_iso_datetime(payload: dict[str, Any], field: str) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None:
        return []
    if isinstance(value, datetime):
        return []
    if not isinstance(value, str):
        return [
            QualityViolation(
                code="invalid_datetime_type",
                message=f"Field '{field}' must be a datetime or ISO string.",
                field=field,
                severity="error",
            )
        ]
    try:
        datetime.fromisoformat(value.strip())
    except ValueError:
        return [
            QualityViolation(
                code="invalid_datetime",
                message=f"Field '{field}' is not a valid ISO datetime.",
                field=field,
                severity="error",
            )
        ]
    return []


def rule_reasonable_amount(
    payload: dict[str, Any], field: str, *, upper_bound: float
) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None:
        return []
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return []
    if value > upper_bound:
        return [
            QualityViolation(
                code="outlier_amount",
                message=f"Field '{field}' exceeds the reasonable upper bound {upper_bound}.",
                field=field,
                severity="warning",
            )
        ]
    return []


def rule_rut(payload: dict[str, Any], field: str) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None:
        return []
    if isinstance(value, int):
        return []
    if not isinstance(value, str):
        return [
            QualityViolation(
                code="invalid_rut_type",
                message=f"Field '{field}' must be a string.",
                field=field,
                severity="error",
            )
        ]
    candidate = value.strip()
    if not candidate:
        return [
            QualityViolation(
                code="invalid_rut",
                message=f"Field '{field}' is empty.",
                field=field,
                severity="error",
            )
        ]
    normalized = candidate.replace(".", "")
    if not _RUT_PATTERN.match(normalized.upper()):
        return [
            QualityViolation(
                code="invalid_rut",
                message=f"Field '{field}' does not look like a Chilean RUT.",
                field=field,
                severity="error",
            )
        ]
    return []


def rule_allowlist(
    payload: dict[str, Any], field: str, *, allowed: set[str]
) -> list[QualityViolation]:
    value = payload.get(field)
    if value is None:
        return []
    if isinstance(value, str) and (
        value.strip().upper() in {a.upper() for a in allowed}
    ):
        return []
    if value in allowed:
        return []
    return [
        QualityViolation(
            code="unexpected_value",
            message=f"Field '{field}' has an unexpected value: {value!r}.",
            field=field,
            severity="warning",
        )
    ]


# ------------------------------------------------------------------------- #
# Composite / high level rules
# ------------------------------------------------------------------------- #
def full_payload_rules(
    payload: dict[str, Any],
    *,
    required_fields: list[str] | None = None,
    rut_fields: list[str] | None = None,
    amount_fields: list[str] | None = None,
    money_upper_bound: float = 0.0,
    datetime_fields: list[str] | None = None,
    allowlist_fields: dict[str, set[str]] | None = None,
    non_negative_fields: list[str] | None = None,
) -> list[QualityViolation]:
    """Evaluate a bundle of quality rules against a fresh report.

    This is an ergonomic dispatcher so callers can validate a transformed
    payload without composing callables manually.
    """
    violations: list[QualityViolation] = []
    for raw_field in required_fields or []:
        violations.extend(rule_required(payload, raw_field))
    for raw_field in rut_fields or []:
        violations.extend(rule_rut(payload, raw_field))
    for raw_field in amount_fields or []:
        violations.extend(rule_positive_number(payload, raw_field))
        if money_upper_bound > 0:
            violations.extend(
                rule_reasonable_amount(
                    payload, raw_field, upper_bound=money_upper_bound
                )
            )
    for raw_field in datetime_fields or []:
        violations.extend(rule_iso_datetime(payload, raw_field))
    for raw_field in non_negative_fields or []:
        violations.extend(rule_non_negative_number(payload, raw_field))
    for raw_field, allowed in (allowlist_fields or {}).items():
        violations.extend(rule_allowlist(payload, raw_field, allowed=allowed))
    return violations


def evaluate_rules(
    payload: dict[str, Any],
    rules: list[QualityRule],
) -> QualityReport:
    """Evaluate a list of rules against a payload and aggregate results."""
    report = QualityReport()
    for rule in rules:
        report.violations.extend(rule(payload))
    # For a "passed check" count we approximate by counting evaluated rules plus
    # the records with no violation.
    report.passed_checks = len(rules)
    return report


__all__ = [
    "QualityViolation",
    "QualityReport",
    "rule_required",
    "rule_non_negative_number",
    "rule_positive_number",
    "rule_iso_datetime",
    "rule_reasonable_amount",
    "rule_rut",
    "rule_allowlist",
    "full_payload_rules",
    "evaluate_rules",
]
