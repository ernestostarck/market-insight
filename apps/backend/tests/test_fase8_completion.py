"""Evidence for the Fase 8 completion criteria.

Each section covers one "Criterio de finalización" / "el sistema deberá permitir conocer" item
with a behavioural check rather than a check that a file exists. Infra-file checks skip when the
repo root is not mounted (the containerised test-runner only mounts ``tests/``).
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import monitoring as monitoring_endpoint
from app.core.middleware import RequestIDMiddleware
from app.core.settings import Settings
from app.main import create_app
from app.monitoring import data_quality
from app.monitoring.health import HealthChecker
from app.monitoring.metrics import (
    ALERTMANAGER_NOTIFICATIONS_RECEIVED_TOTAL,
    CHILECOMPRA_UP,
    DATA_QUALITY_SCORE,
)
from app.nlp.observability import metrics as nlp_metrics
from app.schemas.health import DependencyDetail

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = REPO_ROOT / "docker" / "monitoring" / "prometheus" / "rules"
needs_repo = pytest.mark.skipif(not RULES_DIR.is_dir(), reason="repo infra files not mounted")


def _counter(metric: Any, **labels: str) -> float:
    return metric.labels(**labels)._value.get()


def _alerts() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(RULES_DIR.glob("*.yml")):
        for group in yaml.safe_load(path.read_text(encoding="utf-8"))["groups"]:
            out.extend(rule for rule in group["rules"] if "alert" in rule)
    return out


# --------------------------------------------------------------------------- #
# Alertmanager manages alerts: the webhook it delivers to.
# --------------------------------------------------------------------------- #

_PAYLOAD = {
    "status": "firing",
    "receiver": "critical-notifications",
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "WebhookProbe", "severity": "critical", "team": "backend"},
            "annotations": {"summary": "probe", "description": "password=hunter2-hunter2"},
        }
    ],
}


def _settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, SECRET_KEY="test-secret-key-" + "x" * 32, **overrides)


async def _post(settings: Settings, headers: dict[str, str] | None = None) -> Any:
    app = create_app()
    app.dependency_overrides[monitoring_endpoint.get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/v1/monitoring/alerts/webhook", json=_PAYLOAD, headers=headers or {})


@pytest.mark.asyncio
async def test_webhook_accepts_alertmanager_payload_and_counts_the_notification() -> None:
    labels = {"alertname": "WebhookProbe", "severity": "critical", "status": "firing"}
    before = _counter(ALERTMANAGER_NOTIFICATIONS_RECEIVED_TOTAL, **labels)

    response = await _post(_settings(ENVIRONMENT="development"))

    assert response.status_code == 202
    assert response.json() == {"received": 1}
    assert _counter(ALERTMANAGER_NOTIFICATIONS_RECEIVED_TOTAL, **labels) == before + 1


@pytest.mark.asyncio
async def test_webhook_logs_a_structured_event_without_leaking_secrets(caplog: pytest.LogCaptureFixture) -> None:
    from app.core.logging import JSONFormatter

    with caplog.at_level("INFO", logger="app.alerts"):
        await _post(_settings(ENVIRONMENT="development"))

    record = next(r for r in caplog.records if getattr(r, "event", None) == "alert_notification")
    line = JSONFormatter().format(record)
    assert '"alert_name": "WebhookProbe"' in line
    assert "hunter2" not in line


@pytest.mark.asyncio
async def test_webhook_requires_the_shared_token_when_configured() -> None:
    settings = _settings(ENVIRONMENT="production", ALERT_WEBHOOK_TOKEN="s3cret-token")

    assert (await _post(settings)).status_code == 401
    assert (await _post(settings, {"Authorization": "Bearer wrong"})).status_code == 401
    assert (await _post(settings, {"Authorization": "Bearer s3cret-token"})).status_code == 202


@pytest.mark.asyncio
async def test_webhook_fails_closed_in_production_without_a_token() -> None:
    assert (await _post(_settings(ENVIRONMENT="production", ALERT_WEBHOOK_TOKEN=None))).status_code == 503


# --------------------------------------------------------------------------- #
# Data Quality is measurable: the ETL publishes a score per run.
# --------------------------------------------------------------------------- #

_GOOD = {"codigo": "1-L1", "monto_total": 1000, "fecha_creacion": "2026-01-01"}


def test_invalid_records_lower_the_score_even_though_they_never_reach_the_evaluator() -> None:
    clean = data_quality.evaluate_batch("q_clean", [_GOOD] * 10)
    with_rejects = data_quality.evaluate_batch("q_rejects", [_GOOD] * 5, invalid_count=5)

    assert clean == 100.0
    assert with_rejects < 60.0
    assert _counter(data_quality.INVALID_RECORDS_TOTAL if hasattr(data_quality, "INVALID_RECORDS_TOTAL") else _invalid(), pipeline="q_rejects", reason="failed_validation") == 5


def _invalid() -> Any:
    from app.monitoring.metrics import INVALID_RECORDS_TOTAL

    return INVALID_RECORDS_TOTAL


def test_pipeline_publishes_quality_score_and_never_breaks_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.etl.orchestration import pipeline as etl_pipeline

    etl_pipeline._record_batch_quality("q_pipeline", [_GOOD, _GOOD], invalid=0, duplicates=0)
    assert DATA_QUALITY_SCORE.labels(pipeline="q_pipeline")._value.get() == 100.0

    def boom(*_a: Any, **_k: Any) -> float:
        raise RuntimeError("metrics backend down")

    monkeypatch.setattr(data_quality, "evaluate_batch", boom)
    etl_pipeline._record_batch_quality("q_pipeline", [_GOOD], invalid=0, duplicates=0)  # must not raise


def test_empty_batch_does_not_publish_a_fake_perfect_score() -> None:
    from app.etl.orchestration import pipeline as etl_pipeline

    etl_pipeline._record_batch_quality("q_empty", [], invalid=0, duplicates=0)
    assert ("q_empty",) not in DATA_QUALITY_SCORE._metrics


# --------------------------------------------------------------------------- #
# NLP has operational metrics: the counters the alerts read are actually incremented.
# --------------------------------------------------------------------------- #


def _stub_executor(**overrides: Any) -> Any:
    from app.nlp.semantic import EmbeddingsStageExecutor

    executor = object.__new__(EmbeddingsStageExecutor)
    executor._taxonomy = SimpleNamespace(version="v1")
    executor._model_name = "test-model"
    executor._model_version = "v1"
    executor._classifier = None
    executor._classifier_model_version_id = None
    executor._classifier_dataset_version_id = None
    for key, value in overrides.items():
        setattr(executor, key, value)
    return executor


def test_classification_records_total_and_low_confidence() -> None:
    executor = _stub_executor()
    connection = MagicMock()
    connection.execute.return_value.first.return_value = None  # no prior classification
    connection.execute.return_value.scalar.return_value = True  # tender still open
    context = SimpleNamespace(licitacion_id="lic-1", text_hash="h")

    total = nlp_metrics.NLP_CLASSIFICATIONS_TOTAL.labels(category_code="not_relevant", method="none")
    low = nlp_metrics.NLP_LOW_CONFIDENCE_TOTAL.labels(method="none")
    total_before, low_before = total._value.get(), low._value.get()

    executor._best_match = lambda _v: (0.0, None)
    executor._update_or_create_classification(connection, context, 0.0, None, None, 0.0)

    assert total._value.get() == total_before + 1
    assert low._value.get() == low_before + 1  # confidence 0.0 < 0.70


def test_embedding_failure_is_counted_and_the_stage_reports_failure() -> None:
    class _FailingService:
        def encode(self, _texts: list[str]) -> Any:
            raise RuntimeError("model unavailable")

    connection = MagicMock()
    connection.execute.return_value.first.return_value = ("some normalized text",)
    executor = _stub_executor(_connection_factory=lambda: connection, _embedding_service=_FailingService())
    failures = nlp_metrics.NLP_EMBEDDING_FAILURES_TOTAL.labels(model="test-model")
    before = failures._value.get()

    ok = executor.run(SimpleNamespace(licitacion_id="lic-1", text_hash="h"))

    assert ok is False
    assert failures._value.get() == before + 1
    connection.rollback.assert_called_once()


# --------------------------------------------------------------------------- #
# Worker metrics, logs and error tracking.
# --------------------------------------------------------------------------- #


def test_worker_serves_metrics_once_and_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.worker import observability

    started: list[int] = []
    monkeypatch.setattr(observability, "start_http_server", started.append)
    monkeypatch.setattr(observability, "_metrics_server_started", False)

    monkeypatch.setenv(observability.METRICS_PORT_ENV, "0")
    observability._serve_metrics()
    assert started == []

    monkeypatch.setenv(observability.METRICS_PORT_ENV, "9999")
    observability._serve_metrics()
    observability._serve_metrics()
    assert started == [9999]


def test_worker_replaces_celery_logging_with_the_structured_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.worker import observability

    calls: list[str] = []
    monkeypatch.setattr(observability, "configure_logging", lambda: calls.append("logging"))
    monkeypatch.setattr(observability, "setup_sentry", lambda: calls.append("sentry"))

    observability._configure_worker_logging()
    observability._init_error_tracking()

    assert calls == ["logging", "sentry"]


# --------------------------------------------------------------------------- #
# ChileCompra status is known, as technical reachability (not data freshness).
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "expected"), [("healthy", 1.0), ("degraded", 0.0)])
async def test_chilecompra_probe_publishes_chilecompra_up(
    monkeypatch: pytest.MonkeyPatch, status: str, expected: float
) -> None:
    async def probe(self: HealthChecker, timeout: float) -> DependencyDetail:
        return DependencyDetail(status=status, latency_ms=12.0)

    monkeypatch.setattr(HealthChecker, "_probe_chilecompra", probe)
    await HealthChecker(_settings()).check_chilecompra()

    assert CHILECOMPRA_UP._value.get() == expected


# --------------------------------------------------------------------------- #
# Sentry records errors (end to end, with a capturing transport) and scrubs them.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_sentry_captures_an_unhandled_error_with_request_context_and_no_secrets() -> None:
    import sentry_sdk
    from sentry_sdk.transport import Transport

    from app.core.sentry import filter_sentry_event

    captured: list[dict[str, Any]] = []

    class _Capture(Transport):
        def capture_envelope(self, envelope: Any) -> None:
            for item in envelope.items:
                if item.type == "event":
                    captured.append(item.payload.json)

    sentry_sdk.init(
        dsn="https://public@example.invalid/1",
        transport=_Capture,
        environment="test",
        release="market-insight@9.9.9",
        send_default_pii=False,
        before_send=filter_sentry_event,
    )
    try:
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/boom")
        async def boom() -> None:
            raise RuntimeError("connect failed password=hunter2-hunter2")

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            await client.get("/boom", headers={"X-Request-ID": "sentry-e2e-1", "Authorization": "Bearer abcdefgh12345"})
        sentry_sdk.flush()
    finally:
        sentry_sdk.get_client().close()

    event = next(e for e in captured if "exception" in e)
    assert event["environment"] == "test"
    assert event["release"] == "market-insight@9.9.9"
    assert event["tags"]["request_id"] == "sentry-e2e-1"
    assert event["exception"]["values"][0]["stacktrace"]["frames"]
    rendered = str(event)
    assert "hunter2" not in rendered
    assert "abcdefgh12345" not in rendered


# --------------------------------------------------------------------------- #
# OpenTelemetry allows tracing: the server span carries the request ID.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_trace_span_carries_the_request_id_even_when_the_server_generates_it() -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ping")
    finally:
        FastAPIInstrumentor.uninstrument_app(app)

    request_id = response.headers["X-Request-ID"]
    server_spans = [s for s in exporter.get_finished_spans() if s.attributes.get("app.request_id")]
    assert server_spans and server_spans[0].attributes["app.request_id"] == request_id
    assert server_spans[0].attributes["correlation_id"] == request_id


# --------------------------------------------------------------------------- #
# Infrastructure wiring that the metrics and alerts depend on.
# --------------------------------------------------------------------------- #


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_multi_constructor("!", lambda loader, suffix, node: "__reset__")


def _yaml(rel: str) -> Any:
    return yaml.load((REPO_ROOT / rel).read_text(encoding="utf-8"), Loader=_Loader)


@needs_repo
def test_every_prometheus_job_referenced_by_a_rule_is_actually_scraped() -> None:
    scraped = {job["job_name"] for job in _yaml("docker/monitoring/prometheus/prometheus.yml")["scrape_configs"]}
    referenced = {
        job
        for rule in _alerts()
        for job in re.findall(r'job="([^"]+)"', rule["expr"])
    }
    assert referenced - scraped == set()


@needs_repo
def test_the_etl_queue_has_a_consumer_and_a_scheduler() -> None:
    services = _yaml("docker-compose.yml")["services"]
    commands = {name: " ".join(svc.get("command", [])) for name, svc in services.items()}

    assert any("--queues=market-insight" in c and " worker " in c for c in commands.values())
    assert any(" beat " in c for c in commands.values())


@needs_repo
def test_workers_run_the_threads_pool_so_one_process_owns_the_metrics() -> None:
    services = _yaml("docker-compose.yml")["services"]
    for name in ("nlp-worker", "etl-worker"):
        assert "--pool=threads" in services[name]["command"] if "command" in services[name] else True
    assert "--pool=threads" in (REPO_ROOT / "apps/backend/Dockerfile.worker").read_text(encoding="utf-8")


@needs_repo
def test_prometheus_scrapes_both_workers() -> None:
    jobs = {job["job_name"] for job in _yaml("docker/monitoring/prometheus/prometheus.yml")["scrape_configs"]}
    assert {"nlp-worker", "etl-worker"} <= jobs


@needs_repo
def test_test_stack_does_not_run_the_real_etl_schedule() -> None:
    services = _yaml("docker/compose/docker-compose.test.yml")["services"]
    assert services["etl-worker"]["profiles"] == ["disabled"]
    assert services["etl-beat"]["profiles"] == ["disabled"]


@needs_repo
def test_production_alertmanager_emails_and_authenticates_the_webhook_from_secrets() -> None:
    prod = _yaml("docker/compose/docker-compose.prod.yml")
    config = yaml.safe_load(
        prod["configs"]["alertmanager_prod"]["content"]
        .replace("${ALERT_SMTP_HOST:?ALERT_SMTP_HOST is required (host:port)}", "smtp:587")
        .replace("${ALERT_EMAIL_FROM:?ALERT_EMAIL_FROM is required}", "a@b.c")
        .replace("${ALERT_SMTP_USER:?ALERT_SMTP_USER is required}", "u")
        .replace("${ALERT_EMAIL_TO:?ALERT_EMAIL_TO is required}", "o@b.c")
        .replace("${ALERT_EMAIL_TO}", "o@b.c")
    )

    receivers = {r["name"]: r for r in config["receivers"]}
    assert receivers["critical-notifications"]["email_configs"]
    assert receivers["warning-notifications"]["email_configs"]
    assert "email_configs" not in receivers["info-log-sink"]  # informational never reaches a person
    for receiver in receivers.values():
        for hook in receiver["webhook_configs"]:
            assert hook["http_config"]["authorization"]["credentials_file"].startswith("/run/secrets/")
    assert "smtp_auth_password" not in config["global"]  # only the *_file variant, never inline
    assert set(prod["secrets"]) == {"alert_webhook_token", "alert_smtp_password"}
    assert set(prod["services"]["alertmanager"]["secrets"]) == {"alert_webhook_token", "alert_smtp_password"}


@needs_repo
def test_production_requires_the_webhook_token_and_nginx_hides_the_webhook() -> None:
    text = (REPO_ROOT / "docker/compose/docker-compose.prod.yml").read_text(encoding="utf-8")
    assert re.search(r"ALERT_WEBHOOK_TOKEN: \$\{ALERT_WEBHOOK_TOKEN:\?", text)

    conf = (REPO_ROOT / "docker/nginx/prod/conf.d/default.conf").read_text(encoding="utf-8")
    assert re.search(r"location = /api/v1/monitoring/alerts/webhook \{\s*return 403", conf)


@needs_repo
def test_no_alertmanager_config_ships_example_credentials() -> None:
    for path in (REPO_ROOT / "docker/monitoring/alertmanager").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "example.com" not in text and "smtp_password" not in text, path.name


@needs_repo
def test_promtool_alert_test_file_is_in_sync_with_the_rules() -> None:
    """Every alert in the initial list has a promtool scenario that expects it to fire."""
    tests = yaml.safe_load((RULES_DIR.parent / "tests" / "alerts.test.yml").read_text(encoding="utf-8"))
    firing = {
        check["alertname"]
        for case in tests["tests"]
        for check in case["alert_rule_test"]
        if check["exp_alerts"]
    }
    initial = {
        "APIUnavailable", "PostgreSQLUnavailable", "RedisUnavailable", "ETLFailed", "ETLStale",
        "DataFreshnessWarning", "DataFreshnessCritical", "HighAPIErrorRate5xx", "HighAPILatencyP95",
        "PostgreSQLConnectionSaturation", "RedisMemoryPressure", "NLPHighErrorRate",
        "NLPEmbeddingModelFailure", "DataQualityScoreDegraded", "DataQualityScoreCritical",
    }
    assert initial <= firing


# --------------------------------------------------------------------------- #
# Documentation to respond to critical alerts.
# --------------------------------------------------------------------------- #


@needs_repo
def test_every_critical_alert_has_a_runbook_procedure_under_its_exact_name() -> None:
    runbook = (REPO_ROOT / "docs/ops/runbook-alerts.md").read_text(encoding="utf-8")
    headings = "\n".join(line for line in runbook.splitlines() if line.startswith("### "))

    missing = [r["alert"] for r in _alerts() if r["labels"]["severity"] == "critical" and r["alert"] not in headings]
    assert missing == []


@needs_repo
def test_every_alert_is_mentioned_in_the_runbook() -> None:
    runbook = (REPO_ROOT / "docs/ops/runbook-alerts.md").read_text(encoding="utf-8")
    assert [r["alert"] for r in _alerts() if r["alert"] not in runbook] == []


@needs_repo
def test_runbook_only_references_pipelines_that_exist() -> None:
    from app.etl.orchestration.jobs import DEFAULT_RESOURCES

    runbook = (REPO_ROOT / "docs/ops/runbook-alerts.md").read_text(encoding="utf-8")
    for pipeline in re.findall(r"pipeline\s*=\s*'([a-z_]+)'|pipeline=\"([a-z_]+)\"", runbook):
        assert (pipeline[0] or pipeline[1]) in DEFAULT_RESOURCES


def test_data_freshness_primary_pipeline_is_a_real_etl_resource() -> None:
    from app.etl.orchestration.jobs import DEFAULT_RESOURCES
    from app.monitoring.data_freshness import PRIMARY_PIPELINE

    assert PRIMARY_PIPELINE in DEFAULT_RESOURCES


@pytest.mark.asyncio
async def test_background_probes_are_cancelled_cleanly_on_shutdown() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)
    # reaching here without hanging or raising is the assertion
