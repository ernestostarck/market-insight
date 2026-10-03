"""Generate alerts.test.yml (promtool unit tests) from the rule files.

promtool compares annotations verbatim, so expected annotations are copied from the
rules instead of being duplicated by hand. After editing a rule or a scenario:

    python build_alert_tests.py
    promtool test rules alerts.test.yml      # or: make alert-tests

Every scenario states the input series, when to evaluate, and which alert must (or must
not) be firing. ``None`` as the expected labels means "must NOT fire".
"""

from __future__ import annotations

from pathlib import Path

import yaml

HERE = Path(__file__).parent
RULES = HERE.parent / "rules"

rules = {}
for path in sorted(RULES.glob("*.yml")):
    for group in yaml.safe_load(path.read_text(encoding="utf-8"))["groups"]:
        for rule in group["rules"]:
            if "alert" in rule:
                rules[rule["alert"]] = rule


def expected(alertname: str, series_labels: dict[str, str]) -> dict:
    rule = rules[alertname]
    return {
        "exp_labels": {**rule["labels"], **series_labels},
        "exp_annotations": rule["annotations"],
    }


def scenario(name, series, eval_time, alerts):
    """alerts: {alertname: series_labels dict (must fire) | None (must not fire)}."""
    checks = []
    for alertname, labels in alerts.items():
        checks.append(
            {
                "eval_time": eval_time,
                "alertname": alertname,
                "exp_alerts": [] if labels is None else [expected(alertname, labels)],
            }
        )
    return {
        "name": name,
        "interval": "1m",
        "input_series": [{"series": s, "values": v} for s, v in series],
        "alert_rule_test": checks,
    }


HEALTHY = [
    ('up{job="backend"}', "1x60"),
    ('up{job="postgres-exporter"}', "1x60"),
    ('up{job="redis-exporter"}', "1x60"),
    ('up{job="nlp-worker"}', "1x60"),
    ('etl_last_success_timestamp{pipeline="licitaciones"}', "3600x60"),
    ('data_freshness_seconds', "600x60"),
    ('data_quality_score{pipeline="licitaciones"}', "99x60"),
]

tests = [
    # ---- the 12 initial alerts fire on a controlled failure -------------------------------
    scenario("API unavailable", [('up{job="backend"}', "1 1 0x10")], "6m",
             {"APIUnavailable": {"job": "backend"}}),
    scenario("PostgreSQL unavailable", [('up{job="postgres-exporter"}', "0x10")], "5m",
             {"PostgreSQLUnavailable": {"job": "postgres-exporter"}}),
    scenario("Redis unavailable", [('up{job="redis-exporter"}', "0x10")], "5m",
             {"RedisUnavailable": {"job": "redis-exporter"}}),
    scenario("ETL failed", [('etl_records_failed_total{pipeline="licitaciones"}', "0 0 0 5x30")], "12m",
             {"ETLFailed": {"pipeline": "licitaciones"}}),
    scenario("ETL stale", [('etl_last_success_timestamp{pipeline="licitaciones"}', "-100000x40")], "20m",
             {"ETLStale": {"pipeline": "licitaciones"}}),
    scenario("Data freshness warning only", [("data_freshness_seconds", "70000x60")], "35m",
             {"DataFreshnessWarning": {}, "DataFreshnessCritical": None}),
    scenario("Data freshness critical", [("data_freshness_seconds", "130000x60")], "35m",
             {"DataFreshnessCritical": {}, "DataFreshnessWarning": {}}),
    scenario("High API error rate", [
        ('http_requests_total{status="500"}', "0+10x30"),
        ('http_requests_total{status="200"}', "0+10x30"),
    ], "10m", {"HighAPIErrorRate5xx": {}}),
    scenario("High API latency", [
        ('http_request_duration_seconds_bucket{le="0.5"}', "0x40"),
        ('http_request_duration_seconds_bucket{le="1"}', "0+10x40"),
        ('http_request_duration_seconds_bucket{le="+Inf"}', "0+10x40"),
    ], "15m", {"HighAPILatencyP95": {}}),
    scenario("PostgreSQL connection saturation", [
        ('pg_stat_database_numbackends{instance="pg"}', "95x20"),
        ('pg_settings_max_connections{instance="pg"}', "100x20"),
    ], "10m", {"PostgreSQLConnectionSaturation": {"instance": "pg"}}),
    scenario("Redis memory pressure", [
        ('redis_memory_used_bytes{instance="r"}', "90x20"),
        ('redis_memory_max_bytes{instance="r"}', "100x20"),
    ], "10m", {"RedisMemoryPressure": {"instance": "r"}}),
    scenario("NLP processing failure (error rate)", [
        ('nlp_errors_total{stage="runtime",error_code="ValueError"}', "0+5x40"),
    ], "30m", {"NLPHighErrorRate": {"stage": "runtime", "error_code": "ValueError"}}),
    scenario("NLP embedding failures", [
        ('nlp_embedding_failures_total{model="m"}', "0+2x30"),
    ], "12m", {"NLPEmbeddingModelFailure": {"model": "m"}}),
    scenario("NLP worker down", [('up{job="nlp-worker"}', "0x10")], "5m",
             {"NLPWorkerDown": {"job": "nlp-worker"}}),
    scenario("Data quality degraded (warning after 1h)", [
        ('data_quality_score{pipeline="licitaciones"}', "90x100"),
    ], "70m", {"DataQualityScoreDegraded": {"pipeline": "licitaciones"}, "DataQualityScoreCritical": None}),
    scenario("Data quality critical", [
        ('data_quality_score{pipeline="licitaciones"}', "80x100"),
    ], "20m", {"DataQualityScoreCritical": {"pipeline": "licitaciones"}}),

    # ---- no false positives ----------------------------------------------------------------
    scenario("Healthy platform fires nothing", HEALTHY, "50m", {
        name: None for name in (
            "APIUnavailable", "PostgreSQLUnavailable", "RedisUnavailable", "ETLStale",
            "DataFreshnessWarning", "DataFreshnessCritical", "DataQualityScoreDegraded",
            "NLPWorkerDown", "InstanceDown",
        )
    }),
    # Principle: a change in business volume is not an operational failure.
    scenario("Fewer tenders published while ingestion is healthy: no operational alert", [
        *HEALTHY,
        ('etl_records_processed_total{pipeline="licitaciones",action="read"}', "0+60x20 1200+1x40"),
        ('etl_records_failed_total{pipeline="licitaciones"}', "0x60"),
    ], "50m", {
        name: None for name in (
            "ETLFailed", "ETLHighErrorRate", "ETLStale", "DataFreshnessWarning", "DataFreshnessCritical",
        )
    }),
]

out = HERE / "alerts.test.yml"
header = "# GENERATED by build_alert_tests.py - do not edit by hand.\n"
files = sorted(f"../rules/{p.name}" for p in RULES.glob("*.yml") if p.name != "calibration.yml")
doc = {"rule_files": files, "evaluation_interval": "1m", "tests": tests}
out.write_text(header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
print(f"wrote {out.name}: {len(tests)} scenarios")
