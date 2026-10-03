"""Executable form of the Fase 8 "Principios de implementación".

Each section pins one principle so a regression fails CI instead of silently
undoing it. Infra-file checks skip when the repo root is not mounted (e.g. the
containerised test-runner only mounts ``tests/``).
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Self

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import system as system_endpoint
from app.core.context import get_request_id, reset_request_id, set_request_id
from app.core.logging import ConsoleFormatter, JSONFormatter, redact_text, redact_value
from app.core.middleware import resolve_request_id
from app.core.sentry import filter_sentry_event
from app.main import create_app
from app.monitoring import data_freshness
from app.monitoring.alerts import AlertSeverity, OperationalAlert
from app.monitoring.data_freshness import (
    FRESHNESS_NORMAL_MAX_SECONDS,
    FRESHNESS_WARNING_MAX_SECONDS,
    DataFreshnessReport,
    FreshnessState,
)
from app.monitoring.health import HealthChecker
from app.schemas.health import DependencyDetail

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = REPO_ROOT / "docker" / "monitoring" / "prometheus" / "rules"

needs_repo = pytest.mark.skipif(not RULES_DIR.is_dir(), reason="repo infra files not mounted")


def _load_rules() -> dict[str, list[dict[str, Any]]]:
    files: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(RULES_DIR.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        files[path.name] = [rule for group in doc["groups"] for rule in group["rules"]]
    return files


def _alerts() -> list[tuple[str, dict[str, Any]]]:
    return [(f, r) for f, rules in _load_rules().items() for r in rules if "alert" in r]


# --------------------------------------------------------------------------- #
# 1-3. Alerts need operational context; a volume change is not an outage.
# --------------------------------------------------------------------------- #

_OPERATIONAL_SIGNALS = ("etl_records_failed_total", "etl_last_success_timestamp", "etl_runs_total",
                        "data_freshness_seconds", "up{", "up ==")


@needs_repo
def test_volume_only_alerts_never_page() -> None:
    """A rule that only watches ingestion volume must be informational."""
    offenders = [
        r["alert"]
        for _, r in _alerts()
        if "etl_records_processed_total" in r["expr"]
        and not any(sig in r["expr"] for sig in _OPERATIONAL_SIGNALS)
        and r["labels"]["severity"] != "info"
    ]
    assert offenders == []


@needs_repo
def test_ingestion_volume_drop_is_informational_and_says_it_is_not_a_failure() -> None:
    rule = next(r for _, r in _alerts() if r["alert"] == "ETLIngestionVolumeDrop")
    assert rule["labels"]["severity"] == "info"
    assert "no indica una falla" in rule["annotations"]["description"]


@needs_repo
def test_no_alert_text_asserts_chilecompra_is_down_from_data_signals_alone() -> None:
    claims = re.compile(r"(?i)indisponibilidad de (la )?api chilecompra|chilecompra (est[aá] )?ca[ií]d[oa]")
    offenders = [
        r["alert"]
        for _, r in _alerts()
        if claims.search(r["annotations"].get("summary", "") + r["annotations"].get("description", ""))
    ]
    assert offenders == []


@needs_repo
def test_every_alert_has_severity_and_operational_text() -> None:
    for _, rule in _alerts():
        assert rule["labels"]["severity"] in {"info", "warning", "critical"}, rule["alert"]
        assert rule["annotations"].get("summary"), rule["alert"]
        assert rule["annotations"].get("description"), rule["alert"]


# --------------------------------------------------------------------------- #
# 4. Technical availability and data availability are assessed separately.
# --------------------------------------------------------------------------- #


def _dep(status: str) -> DependencyDetail:
    return DependencyDetail(status=status, latency_ms=1.0)


def _freshness(state: FreshnessState, seconds: float) -> DataFreshnessReport:
    return DataFreshnessReport(status=state, freshness_seconds=seconds, source="test")


@pytest.fixture
def status_env(monkeypatch: pytest.MonkeyPatch):
    """Patch probes and freshness so each case controls both layers independently."""

    def configure(
        *,
        postgres="healthy",
        chilecompra="healthy",
        quality: float = 100.0,
        freshness: DataFreshnessReport,
    ):
        async def fake(status: str):
            return _dep(status)

        async def pg(self, timeout=2.0):
            return await fake(postgres)

        async def redis(self, timeout=2.0):
            return await fake("healthy")

        async def storage(self, timeout=2.0):
            return await fake("healthy")

        async def cc(self, timeout=3.0):
            return await fake(chilecompra)

        async def refresh(*args, **kwargs):
            return freshness

        monkeypatch.setattr(HealthChecker, "check_postgres", pg)
        monkeypatch.setattr(HealthChecker, "check_redis", redis)
        monkeypatch.setattr(HealthChecker, "check_storage", storage)
        monkeypatch.setattr(HealthChecker, "check_chilecompra", cc)
        monkeypatch.setattr(system_endpoint, "refresh_data_freshness", refresh)
        # The quality gauge is process-global; pin it so other tests cannot leak into this one.
        monkeypatch.setattr(system_endpoint, "_get_metric_gauge_value", lambda *a, **k: quality)

    return configure


async def _system_status() -> dict[str, Any]:
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        response = await client.get("/api/v1/system/status")
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_stale_data_with_healthy_platform_is_a_data_problem_not_an_outage(status_env) -> None:
    status_env(freshness=_freshness(FreshnessState.CRITICAL, 200_000.0))
    body = await _system_status()

    assert body["availability"]["technical"]["status"] == "healthy"
    assert body["availability"]["data"]["status"] == "unhealthy"
    assert body["status"] != "unhealthy"
    assert body["etl"]["status"] == "stale"


@pytest.mark.asyncio
async def test_stale_data_points_at_the_pipeline_when_chilecompra_is_reachable(status_env) -> None:
    status_env(chilecompra="healthy", freshness=_freshness(FreshnessState.CRITICAL, 200_000.0))
    reasons = (await _system_status())["availability"]["data"]["reasons"]

    assert any("ETL pipeline" in r for r in reasons)


@pytest.mark.asyncio
async def test_stale_data_only_suspects_upstream_when_chilecompra_is_unreachable(status_env) -> None:
    status_env(chilecompra="degraded", freshness=_freshness(FreshnessState.CRITICAL, 200_000.0))
    body = await _system_status()

    assert any("unreachable" in r for r in body["availability"]["data"]["reasons"])
    assert body["availability"]["technical"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_database_outage_is_technical_and_leaves_data_layer_untouched(status_env) -> None:
    status_env(postgres="unhealthy", freshness=_freshness(FreshnessState.NORMAL, 60.0))
    body = await _system_status()

    assert body["availability"]["technical"]["status"] == "unhealthy"
    assert body["availability"]["data"]["status"] == "healthy"
    assert body["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_freshness_warning_does_not_break_system_status(status_env) -> None:
    """Regression: ETLStatusSummary rejected "degraded" and /system/status returned 500."""
    status_env(freshness=_freshness(FreshnessState.WARNING, 70_000.0))
    body = await _system_status()

    assert body["etl"]["status"] == "degraded"
    assert body["availability"]["technical"]["status"] == "healthy"


# --------------------------------------------------------------------------- #
# 5. data_freshness detects ingestion problems, and is really computed.
# --------------------------------------------------------------------------- #


@needs_repo
def test_freshness_alert_thresholds_match_the_code_that_classifies_freshness() -> None:
    rules = {r["alert"]: r for _, r in _alerts()}
    assert f"> {FRESHNESS_NORMAL_MAX_SECONDS:.0f}" in rules["DataFreshnessWarning"]["expr"]
    assert f"> {FRESHNESS_WARNING_MAX_SECONDS:.0f}" in rules["DataFreshnessCritical"]["expr"]
    assert rules["DataFreshnessWarning"]["labels"]["severity"] == "warning"
    assert rules["DataFreshnessCritical"]["labels"]["severity"] == "critical"


class _FakeSession:
    def __init__(self, value: datetime | None) -> None:
        self._value = value

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def scalar(self, _stmt: object) -> datetime | None:
        return self._value


@pytest.mark.asyncio
async def test_freshness_gauge_is_computed_from_the_persisted_etl_run_log() -> None:
    """Workers run the ETL, the API serves the gauge: the run log is what they share."""
    three_hours_ago = datetime.now(UTC) - timedelta(hours=3)
    report = await data_freshness.refresh_data_freshness(
        session_factory=lambda: _FakeSession(three_hours_ago)
    )

    assert report.source == "etl_runs"
    assert report.status == FreshnessState.NORMAL
    assert 3 * 3600 - 5 <= report.freshness_seconds <= 3 * 3600 + 5
    assert 3 * 3600 - 5 <= data_freshness.DATA_FRESHNESS_SECONDS._value.get() <= 3 * 3600 + 5


@pytest.mark.asyncio
async def test_freshness_refresh_survives_an_unreachable_database() -> None:
    def broken() -> Any:
        raise ConnectionError("db down")

    report = await data_freshness.refresh_data_freshness(session_factory=broken)
    assert isinstance(report, DataFreshnessReport)


@pytest.mark.asyncio
async def test_freshness_refresher_loop_keeps_running_after_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def flaky(pipeline: str = "x") -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")

    monkeypatch.setattr(data_freshness, "refresh_data_freshness", flaky)
    task = asyncio.create_task(data_freshness.run_freshness_refresher(interval_seconds=0.01))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls >= 2


def test_unobserved_quality_gauge_is_unknown_not_zero() -> None:
    from prometheus_client import CollectorRegistry, Gauge

    gauge = Gauge("q_score", "test", ["pipeline"], registry=CollectorRegistry())
    assert system_endpoint._get_metric_gauge_value(gauge, pipeline="never_ran") is None
    gauge.labels(pipeline="seen").set(97.5)
    assert system_endpoint._get_metric_gauge_value(gauge, pipeline="seen") == 97.5


# --------------------------------------------------------------------------- #
# 6. Real metrics before definitive thresholds.
# --------------------------------------------------------------------------- #


@needs_repo
def test_calibration_recording_rules_cover_every_threshold_family() -> None:
    calibration = {r["record"] for r in _load_rules()["calibration.yml"]}
    assert {
        "calibration:data_freshness_seconds:p95_7d",
        "calibration:data_quality_score:min_7d",
        "calibration:http_request_duration_seconds:p95_1d",
        "calibration:http_error_ratio:max_7d",
        "calibration:etl_duration_seconds:p95_7d",
        "calibration:nlp_low_confidence_ratio:avg_7d",
    } <= calibration


@needs_repo
def test_calibration_rules_only_record_and_never_alert() -> None:
    assert all("alert" not in r for r in _load_rules()["calibration.yml"])


@needs_repo
def test_rules_are_identical_in_both_monitoring_trees() -> None:
    other = REPO_ROOT / "infrastructure" / "monitoring" / "prometheus" / "rules"
    if not other.is_dir():
        pytest.skip("infrastructure tree not present")
    for path in RULES_DIR.glob("*.yml"):
        assert (other / path.name).read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), path.name


# --------------------------------------------------------------------------- #
# 7. Observability tooling stays protected.
# --------------------------------------------------------------------------- #


class _Loader(yaml.SafeLoader):
    """SafeLoader that tolerates Compose's ``!reset`` / ``!override`` tags."""


_Loader.add_multi_constructor("!", lambda loader, suffix, node: "__reset__")


def _compose(name: str) -> dict[str, Any]:
    path = REPO_ROOT / name
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)["services"]


_PUBLIC = {"nginx", "frontend"}


@needs_repo
def test_base_compose_binds_every_internal_service_to_loopback() -> None:
    for name, service in _compose("docker-compose.yml").items():
        if name in _PUBLIC:
            continue
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name} publishes {port} on all interfaces"


@needs_repo
def test_production_overlay_publishes_only_nginx() -> None:
    overlay = _compose("docker/compose/docker-compose.prod.yml")
    for name, service in overlay.items():
        ports = service.get("ports")
        if name == "nginx":
            assert ports and ports != "__reset__"
            continue
        assert ports in (None, "__reset__", []), f"{name} may publish ports in production"


@needs_repo
def test_production_overlay_does_not_deploy_database_admin_tools() -> None:
    overlay = _compose("docker/compose/docker-compose.prod.yml")
    for tool in ("pgadmin", "redisinsight"):
        assert overlay[tool]["profiles"] == ["disabled"]


@needs_repo
def test_production_nginx_protects_observability_endpoints() -> None:
    conf = (REPO_ROOT / "docker/nginx/prod/conf.d/default.conf").read_text(encoding="utf-8")

    assert re.search(r"location = /metrics \{\s*return 403", conf)
    for prefix in ("/grafana/", "/alertmanager/"):
        block = re.search(rf"location {re.escape(prefix)} \{{(.*?)\n  \}}", conf, re.DOTALL)
        assert block and "auth_basic_user_file" in block.group(1), prefix
    assert "location /prometheus" not in conf


@needs_repo
def test_production_secrets_have_no_defaults() -> None:
    text = (REPO_ROOT / "docker/compose/docker-compose.prod.yml").read_text(encoding="utf-8")
    for var in ("SECRET_KEY", "GRAFANA_ADMIN_PASSWORD", "POSTGRES_PASSWORD", "REDIS_PASSWORD"):
        assert re.search(rf"\$\{{{var}:\?", text), var


# --------------------------------------------------------------------------- #
# 8. Secrets stay out of logs and observability systems.
# --------------------------------------------------------------------------- #

_SECRETS = [
    "eyJhbGciOiJIUzI1NiJ9.payload.signature",
    "s3cr3t-Passw0rd",
    "ABCD-1234-TICKET-9999",
]


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        (f"Authorization: Bearer {_SECRETS[0]}", _SECRETS[0]),
        (f"login failed password={_SECRETS[1]} for user", _SECRETS[1]),
        (f"GET https://api.mercadopublico.cl/x?ticket={_SECRETS[2]}&fecha=01012026", _SECRETS[2]),
        (f"postgresql://app:{_SECRETS[1]}@postgres:5432/db", _SECRETS[1]),
        (f'payload {{"api_key": "{_SECRETS[2]}", "n": 1}}', _SECRETS[2]),
        (f"CHILECOMPRA_API_KEY: {_SECRETS[2]}", _SECRETS[2]),
    ],
)
def test_redact_text_masks_secrets_embedded_in_free_text(text: str, secret: str) -> None:
    assert secret not in redact_text(text)


def test_redact_text_keeps_ordinary_operational_messages_intact() -> None:
    message = "Ingested 150 tenders in 2.4s (inserted=120 updated=30 failed=0)"
    assert redact_text(message) == message


def test_redact_value_masks_nested_structures() -> None:
    cleaned = redact_value({"headers": {"Authorization": _SECRETS[0], "X-Trace": "ok"}, "items": [{"db_password": "x"}]})

    assert cleaned["headers"]["Authorization"] == "***REDACTED***"
    assert cleaned["headers"]["X-Trace"] == "ok"
    assert cleaned["items"][0]["db_password"] == "***REDACTED***"


def _record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("t", logging.ERROR, __file__, 1, msg, (), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_logs_redact_message_error_and_nested_extra() -> None:
    line = JSONFormatter().format(
        _record(f"request failed token={_SECRETS[0]}", context={"cookie": _SECRETS[1], "path": "/x"})
    )

    for secret in _SECRETS[:2]:
        assert secret not in line


def test_json_logs_redact_exception_text() -> None:
    try:
        raise RuntimeError(f"connect failed postgresql://app:{_SECRETS[1]}@db/x")
    except RuntimeError:
        import sys

        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "boom", (), sys.exc_info())
    assert _SECRETS[1] not in JSONFormatter().format(record)


def test_console_logs_redact_secrets() -> None:
    record = _record(f"retry with api_key={_SECRETS[2]}")
    record.request_id = "-"
    assert _SECRETS[2] not in ConsoleFormatter().format(record)


def test_numeric_extras_named_like_secrets_are_kept() -> None:
    line = JSONFormatter().format(_record("done", token_count=42))
    assert '"token_count": 42' in line


def test_sentry_events_are_scrubbed_of_secrets_in_text_and_breadcrumbs() -> None:
    event = {
        "message": f"failed password={_SECRETS[1]}",
        "exception": {"values": [{"value": f"bad token={_SECRETS[0]}"}]},
        "breadcrumbs": {"values": [{"message": f"ticket={_SECRETS[2]}", "data": {"authorization": _SECRETS[0]}}]},
        "request": {"headers": {"Authorization": f"Bearer {_SECRETS[0]}"}},
    }
    rendered = str(filter_sentry_event(event, {}))

    for secret in _SECRETS:
        assert secret not in rendered


def test_alert_payloads_never_carry_secrets() -> None:
    alert = OperationalAlert(
        name="X",
        summary=f"failure token={_SECRETS[0]}",
        severity=AlertSeverity.WARNING,
        description=f"dsn postgresql://app:{_SECRETS[1]}@db/x",
        labels={"detail": f"ticket={_SECRETS[2]}"},
    )
    assert not any(secret in str(alert.to_alertmanager_dict()) for secret in _SECRETS)


# --------------------------------------------------------------------------- #
# 9. Traceability through X-Request-ID.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("valid", ["abc-123", "8f14e45f-ceea-467a-9575-ab4f3c9dd5d6", "front.end_1"])
def test_well_formed_request_ids_are_kept(valid: str) -> None:
    assert resolve_request_id(valid) == valid


@pytest.mark.parametrize("hostile", ["a b", "id;drop", "x" * 129, "line\nbreak", "<script>", ""])
def test_hostile_request_ids_are_replaced_with_a_uuid(hostile: str) -> None:
    resolved = resolve_request_id(hostile)
    assert resolved != hostile
    assert re.fullmatch(r"[0-9a-f-]{36}", resolved)


def test_missing_request_id_is_generated() -> None:
    assert re.fullmatch(r"[0-9a-f-]{36}", resolve_request_id(None))


@pytest.mark.asyncio
async def test_response_and_error_body_carry_the_same_request_id() -> None:
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        response = await client.get("/api/v1/does-not-exist", headers={"X-Request-ID": "trace-me-42"})

    assert response.headers["X-Request-ID"] == "trace-me-42"
    assert response.json().get("request_id") in (None, "trace-me-42")


def test_sentry_events_are_tagged_with_the_current_request_id() -> None:
    token = set_request_id("sentry-corr-1")
    try:
        assert filter_sentry_event({}, {})["tags"]["request_id"] == "sentry-corr-1"
    finally:
        reset_request_id(token)


def test_request_id_crosses_the_celery_boundary() -> None:
    from app.worker import tracing

    token = set_request_id("api-req-7")
    try:
        headers: dict[str, Any] = {}
        tracing._inject_request_id(headers=headers)
    finally:
        reset_request_id(token)
    assert headers[tracing.REQUEST_ID_HEADER] == "api-req-7"
    assert get_request_id() == ""

    class _Task:
        request = type("R", (), {tracing.REQUEST_ID_HEADER: "api-req-7"})()

    tracing._restore_request_id(task_id="t1", task=_Task())
    assert get_request_id() == "api-req-7"
    tracing._clear_request_id(task_id="t1")
    assert get_request_id() == ""


def test_celery_publish_without_a_request_context_adds_no_header() -> None:
    from app.worker import tracing

    headers: dict[str, Any] = {}
    tracing._inject_request_id(headers=headers)
    assert tracing.REQUEST_ID_HEADER not in headers


@needs_repo
def test_nginx_forwards_or_generates_x_request_id() -> None:
    conf = (REPO_ROOT / "docker/nginx/prod/conf.d/default.conf").read_text(encoding="utf-8")
    assert "map $http_x_request_id $request_id_value" in conf
    # on the TLS server, every location that redefines proxy_set_header must forward it too
    tls_server = conf[conf.index("listen 443") :]
    for block in re.findall(r"location [^{]+\{(.*?)\n  \}", tls_server, re.DOTALL):
        if "proxy_set_header" in block:
            assert "X-Request-ID" in block


# --------------------------------------------------------------------------- #
# 10. Infrastructure, application, data and NLP metrics stay separate.
# --------------------------------------------------------------------------- #

_LAYER_PREFIXES = {
    "application": ("http_", "alertmanager_"),
    "integration": ("chilecompra_",),
    "data": ("etl_", "data_", "duplicate_", "invalid_"),
    "nlp": ("nlp_",),
}
_INFRA_PREFIXES = ("node_", "container_", "pg_", "redis_", "process_", "up")


def _defined_metric_names(module_path: Path) -> list[str]:
    text = module_path.read_text(encoding="utf-8")
    return re.findall(r'(?:Counter|Gauge|Histogram|Summary)\(\s*"([a-z_:0-9]+)"', text)


def test_nlp_metrics_are_defined_only_in_the_nlp_module_and_all_prefixed() -> None:
    app_dir = Path(__file__).resolve().parents[1] / "app"
    nlp_names = _defined_metric_names(app_dir / "nlp" / "observability" / "metrics.py")
    core_names = _defined_metric_names(app_dir / "monitoring" / "metrics.py")

    assert nlp_names and all(n.startswith("nlp_") for n in nlp_names)
    assert not [n for n in core_names if n.startswith("nlp_")]


def test_application_and_data_metrics_do_not_use_another_layers_prefix() -> None:
    app_dir = Path(__file__).resolve().parents[1] / "app"
    for name in _defined_metric_names(app_dir / "monitoring" / "metrics.py"):
        assert name.startswith(
            _LAYER_PREFIXES["application"] + _LAYER_PREFIXES["data"] + _LAYER_PREFIXES["integration"]
        ), name


@needs_repo
@pytest.mark.parametrize(
    ("rule_file", "allowed"),
    [
        ("api.yml", ("http_", "up")),
        ("etl.yml", ("etl_",)),
        ("data-quality.yml", ("data_", "duplicate_", "invalid_")),
        ("nlp.yml", ("nlp_", "up")),
    ],
)
def test_each_rule_file_only_reads_its_own_layer(rule_file: str, allowed: tuple[str, ...]) -> None:
    other_layers = tuple(p for prefixes in _LAYER_PREFIXES.values() for p in prefixes if p not in allowed)
    for rule in _load_rules()[rule_file]:
        metrics = re.findall(r"\b([a-z][a-z_]+)(?=[{\[(]|\s|$)", rule.get("expr", ""))
        leaked = [m for m in metrics if m.startswith(other_layers)]
        assert leaked == [], f"{rule.get('alert')} mixes layers: {leaked}"


@needs_repo
def test_infrastructure_rules_read_no_application_data_or_nlp_metrics() -> None:
    app_prefixes = tuple(p for prefixes in _LAYER_PREFIXES.values() for p in prefixes)
    for rule in _load_rules()["infrastructure.yml"]:
        metrics = re.findall(r"\b([a-z][a-z_]+)(?=[{\[(]|\s|$)", rule.get("expr", ""))
        assert not [m for m in metrics if m.startswith(app_prefixes)], rule.get("alert")
