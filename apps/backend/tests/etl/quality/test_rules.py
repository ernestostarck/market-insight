from __future__ import annotations

from datetime import datetime, timezone

from app.etl.quality.rules import (
    evaluate_rules,
    full_payload_rules,
    rule_allowlist,
    rule_iso_datetime,
    rule_non_negative_number,
    rule_positive_number,
    rule_required,
    rule_rut,
)


def test_rule_required_pass_when_present() -> None:
    assert rule_required({"external_id": "1000-1"}, "external_id") == []


def test_rule_required_error_when_missing_or_empty() -> None:
    violations = rule_required({"external_id": ""}, "external_id")
    assert len(violations) == 1
    assert violations[0].code == "missing_value"
    assert violations[0].severity == "error"

    assert rule_required({}, "external_id")[0].code == "missing_value"


def test_rule_positive_number() -> None:
    assert rule_positive_number({"amount": 100}, "amount") == []
    violations = rule_positive_number({"amount": 0}, "amount")
    assert violations[0].code == "non_positive_number"
    assert (
        rule_positive_number({"amount": -5}, "amount")[0].code == "non_positive_number"
    )


def test_rule_non_negative_number() -> None:
    assert rule_non_negative_number({"amount": 0}, "amount") == []
    assert rule_non_negative_number({"amount": 10}, "amount") == []
    assert (
        rule_non_negative_number({"amount": -1}, "amount")[0].code == "negative_number"
    )


def test_rule_iso_datetime_accepts_datetime_and_iso_string() -> None:
    assert (
        rule_iso_datetime({"ts": datetime(2026, 8, 6, tzinfo=timezone.utc)}, "ts") == []
    )
    assert rule_iso_datetime({"ts": "2026-08-06T00:00:00+00:00"}, "ts") == []
    violations = rule_iso_datetime({"ts": "not-a-date"}, "ts")
    assert violations[0].code == "invalid_datetime"


def test_rule_rut_accepts_valid_rut() -> None:
    assert rule_rut({"rut": "76123456-7"}, "rut") == []
    assert rule_rut({"rut": "12.345.678-K"}, "rut") == []


def test_rule_rut_rejects_invalid_rut() -> None:
    violations = rule_rut({"rut": "123"}, "rut")
    assert violations[0].code == "invalid_rut"
    assert violations[0].severity == "error"


def test_rule_allowlist() -> None:
    assert (
        rule_allowlist({"status": "activa"}, "status", allowed={"ACTIVA", "ADJUDICADA"})
        == []
    )
    violations = rule_allowlist({"status": "ZOMBIE"}, "status", allowed={"ACTIVA"})
    assert violations[0].code == "unexpected_value"


def test_full_payload_rules_bundle() -> None:
    payload = {
        "external_id": "1000-1-LR26",
        "rut": "76123456-7",
        "amount": 5000,
        "published_at": "2026-08-06T00:00:00+00:00",
        "state": "ADJUDICADA",
    }
    violations = full_payload_rules(
        payload,
        required_fields=["external_id"],
        rut_fields=["rut"],
        amount_fields=["amount"],
        money_upper_bound=10000,
        datetime_fields=["published_at"],
        allowlist_fields={"state": {"ADJUDICADA", "PUBLICADA"}},
        non_negative_fields=["amount"],
    )

    assert violations == []


def test_full_payload_rules_flags_problems() -> None:
    violations = full_payload_rules(
        {"amount": -1},
        required_fields=["external_id"],
        amount_fields=["amount"],
    )
    codes = {v.code for v in violations}
    assert "missing_value" in codes
    assert "negative_number" in codes or "non_positive_number" in codes


def test_evaluate_rules_aggregates_report() -> None:
    payload = {"rut": "123", "amount": -1}
    report = evaluate_rules(
        payload,
        [
            lambda p: rule_rut(p, "rut"),
            lambda p: rule_non_negative_number(p, "amount"),
        ],
    )

    assert report.is_clean is False
    assert len(report.violations) == 2
    assert report.error_count >= 2
    assert report.passed_checks == 2
