from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

logger = logging.getLogger(__name__)

# Calibrated latency buckets for web APIs to compute P95 and P99 accurately
LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    10.0,
)

# Custom HTTP Errors counter to categorize client vs server operational failures
HTTP_ERRORS_TOTAL = Counter(
    "http_errors_total",
    "Total HTTP error responses categorized by error class.",
    ["method", "handler", "status_code", "error_class"],
)

# Application specific business & operational metrics
DATA_FRESHNESS_SECONDS = Gauge(
    "data_freshness_seconds",
    "Data freshness delta in seconds between latest processed tender and current time.",
)
API_DATA_FRESHNESS_SECONDS = DATA_FRESHNESS_SECONDS


# Alert notifications delivered by Alertmanager to the alert webhook
ALERTMANAGER_NOTIFICATIONS_RECEIVED_TOTAL = Counter(
    "alertmanager_notifications_received_total",
    "Alert notifications received from Alertmanager by name, severity and status.",
    ["alertname", "severity", "status"],
)

# Technical availability of the upstream ChileCompra API, independent of data freshness
CHILECOMPRA_UP = Gauge(
    "chilecompra_up",
    "1 if the ChileCompra public API answered the last probe, 0 if not. Says nothing about data freshness.",
)
CHILECOMPRA_PROBE_LATENCY_SECONDS = Gauge(
    "chilecompra_probe_latency_seconds",
    "Round-trip time of the last ChileCompra availability probe.",
)

# ETL Pipeline operational metrics (Fase 8.7)
ETL_RUNS_TOTAL = Counter(
    "etl_runs_total",
    "Total ETL pipeline runs executed.",
    ["pipeline", "status"],
)

ETL_RECORDS_PROCESSED_TOTAL = Counter(
    "etl_records_processed_total",
    "Total records processed by ETL pipelines by action.",
    ["pipeline", "action"],
)

ETL_RECORDS_FAILED_TOTAL = Counter(
    "etl_records_failed_total",
    "Total records that failed during ETL pipeline extraction, transformation or load.",
    ["pipeline"],
)

ETL_DURATION_SECONDS = Histogram(
    "etl_duration_seconds",
    "Duration of ETL pipeline runs in seconds.",
    ["pipeline"],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0),
)

ETL_LAST_SUCCESS_TIMESTAMP = Gauge(
    "etl_last_success_timestamp",
    "Epoch timestamp in seconds of the last successful ETL pipeline run.",
    ["pipeline"],
)

# Data Quality operational metrics (Fase 8.8)
DATA_QUALITY_SCORE = Gauge(
    "data_quality_score",
    "Reproducible data quality score (0 to 100) computed for each pipeline.",
    ["pipeline"],
)

DUPLICATE_RECORDS_TOTAL = Counter(
    "duplicate_records_total",
    "Total duplicate records detected during ETL ingestion.",
    ["pipeline"],
)

INVALID_RECORDS_TOTAL = Counter(
    "invalid_records_total",
    "Total invalid records detected by validation reason.",
    ["pipeline", "reason"],
)


def record_data_quality_metrics(
    pipeline: str,
    score: float,
    *,
    duplicates: int = 0,
    invalid_counts: dict[str, int] | None = None,
) -> None:
    """Record computed data quality score and violation counters."""
    DATA_QUALITY_SCORE.labels(pipeline=pipeline).set(round(max(0.0, min(100.0, score)), 2))
    if duplicates > 0:
        DUPLICATE_RECORDS_TOTAL.labels(pipeline=pipeline).inc(duplicates)
    if invalid_counts:
        for reason, count in invalid_counts.items():
            if count > 0:
                INVALID_RECORDS_TOTAL.labels(pipeline=pipeline, reason=reason).inc(count)


def record_etl_run_start(pipeline: str) -> None:
    """Record the start of an ETL run."""
    ETL_RUNS_TOTAL.labels(pipeline=pipeline, status="running").inc()


def record_etl_run_success(
    pipeline: str,
    duration_seconds: float,
    *,
    records_read: int = 0,
    records_inserted: int = 0,
    records_updated: int = 0,
    records_failed: int = 0,
) -> None:
    """Record a successful ETL run and update all corresponding metrics."""
    ETL_RUNS_TOTAL.labels(pipeline=pipeline, status="success").inc()
    ETL_DURATION_SECONDS.labels(pipeline=pipeline).observe(max(duration_seconds, 0.0))
    ETL_LAST_SUCCESS_TIMESTAMP.labels(pipeline=pipeline).set(time.time())

    if records_read > 0:
        ETL_RECORDS_PROCESSED_TOTAL.labels(pipeline=pipeline, action="read").inc(records_read)
    if records_inserted > 0:
        ETL_RECORDS_PROCESSED_TOTAL.labels(pipeline=pipeline, action="inserted").inc(records_inserted)
    if records_updated > 0:
        ETL_RECORDS_PROCESSED_TOTAL.labels(pipeline=pipeline, action="updated").inc(records_updated)
    if records_failed > 0:
        ETL_RECORDS_FAILED_TOTAL.labels(pipeline=pipeline).inc(records_failed)


def record_etl_run_failure(
    pipeline: str,
    duration_seconds: float | None = None,
    *,
    records_failed: int = 0,
) -> None:
    """Record a failed ETL pipeline run."""
    ETL_RUNS_TOTAL.labels(pipeline=pipeline, status="failed").inc()
    if duration_seconds is not None:
        ETL_DURATION_SECONDS.labels(pipeline=pipeline).observe(max(duration_seconds, 0.0))
    if records_failed > 0:
        ETL_RECORDS_FAILED_TOTAL.labels(pipeline=pipeline).inc(records_failed)


def _http_errors_metric() -> Callable[[Info], None]:
    """Custom metric callback for Instrumentator to record 4xx and 5xx errors."""

    def instrumentation(info: Info) -> None:
        status_code = info.response.status_code if info.response else 500
        if status_code >= 400:
            error_class = "server_error" if status_code >= 500 else "client_error"
            handler = info.modified_handler or "unknown"
            HTTP_ERRORS_TOTAL.labels(
                method=info.request.method,
                handler=handler,
                status_code=str(status_code),
                error_class=error_class,
            ).inc()

    return instrumentation


def create_instrumentator() -> Instrumentator:
    """Create and configure the Prometheus Instrumentator for FastAPI."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=False,
        should_group_untemplated=True,
        should_round_latency_decimals=True,
        round_latency_decimals=4,
        excluded_handlers=["/metrics", "/health/live"],
    )

    # 1. Total Requests Counter: http_requests_total
    instrumentator.add(
        metrics.requests(
            metric_name="http_requests_total",
            metric_doc="Total HTTP requests processed by endpoint handler and status code.",
            should_include_method=True,
            should_include_status=True,
            should_include_handler=True,
        )
    )

    # 2. Latency Histogram: http_request_duration_seconds (with calibrated P95/P99 buckets)
    instrumentator.add(
        metrics.latency(
            metric_name="http_request_duration_seconds",
            metric_doc="HTTP request duration in seconds for computing P95 and P99 percentiles.",
            should_include_method=True,
            should_include_status=True,
            should_include_handler=True,
            buckets=LATENCY_BUCKETS,
        )
    )

    # 3. Payload size metrics
    instrumentator.add(metrics.request_size())
    instrumentator.add(metrics.response_size())

    # 4. Error breakdown
    instrumentator.add(_http_errors_metric())

    return instrumentator


def setup_metrics(app: FastAPI) -> Instrumentator:
    """Instrument the FastAPI application and expose /metrics endpoint."""
    instrumentator = create_instrumentator()
    instrumentator.instrument(app)
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["monitoring"],
    )
    logger.info("FastAPI Prometheus metrics instrumentator initialized on /metrics")
    return instrumentator
