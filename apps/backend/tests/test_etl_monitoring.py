"""Tests for ETL monitoring metrics and run persistence (Fase 8.7)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.etl_run import ETLRun
from app.monitoring.etl import record_sync_outcome, record_sync_start
from app.monitoring.metrics import (
    ETL_LAST_SUCCESS_TIMESTAMP,
    ETL_RECORDS_FAILED_TOTAL,
    ETL_RECORDS_PROCESSED_TOTAL,
    ETL_RUNS_TOTAL,
)


@pytest.mark.asyncio
async def test_etl_run_model_instantiation():
    """Verify ETLRun model fields and default values."""
    now = datetime.now(UTC)
    run = ETLRun(
        run_id="etl-licitaciones-test-01",
        pipeline="licitaciones",
        source="chilecompra_api",
        trigger="schedule",
        status="success",
        started_at=now,
        finished_at=now,
        duration_seconds=12.345,
        records_read=150,
        records_inserted=120,
        records_updated=30,
        records_failed=0,
        error_count=0,
    )
    assert run.run_id == "etl-licitaciones-test-01"
    assert run.pipeline == "licitaciones"
    assert run.records_read == 150
    assert run.records_inserted == 120
    assert run.status == "success"
    assert run.duration_seconds == 12.345


@pytest.mark.asyncio
async def test_record_sync_start_and_outcome_metrics():
    """Verify recording sync lifecycle updates Prometheus counters and gauges."""
    pipeline = "licitaciones"
    run_id = record_sync_start(pipeline=pipeline)
    assert run_id.startswith("etl-licitaciones-")

    start_val = ETL_RUNS_TOTAL.labels(pipeline=pipeline, status="running")._value.get()
    assert start_val >= 1.0

    t0 = datetime.now(UTC)
    record_sync_outcome(
        run_id=run_id,
        pipeline=pipeline,
        source="chilecompra_api",
        status="succeeded",
        started_at=t0,
        finished_at=t0,
        duration_seconds=5.2,
        metrics={
            "extracted": 42,
            "inserted": 30,
            "updated": 10,
            "failed": 2,
        },
    )

    success_val = ETL_RUNS_TOTAL.labels(pipeline=pipeline, status="success")._value.get()
    assert success_val >= 1.0

    read_records = ETL_RECORDS_PROCESSED_TOTAL.labels(pipeline=pipeline, action="read")._value.get()
    assert read_records >= 42.0

    failed_records = ETL_RECORDS_FAILED_TOTAL.labels(pipeline=pipeline)._value.get()
    assert failed_records >= 2.0

    last_ts = ETL_LAST_SUCCESS_TIMESTAMP.labels(pipeline=pipeline)._value.get()
    assert last_ts > 0


@pytest.mark.asyncio
async def test_record_sync_failure_metrics():
    """Verify that recording a failed sync increments failed counters."""
    pipeline = "ordenes_compra"
    t0 = datetime.now(UTC)

    record_sync_outcome(
        run_id="failed-run-123",
        pipeline=pipeline,
        source="chilecompra_api",
        status="failed",
        started_at=t0,
        finished_at=t0,
        duration_seconds=1.5,
        error="Connection timeout",
        metrics={"failed": 5},
    )

    fail_runs = ETL_RUNS_TOTAL.labels(pipeline=pipeline, status="failed")._value.get()
    assert fail_runs >= 1.0


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_etl_metrics():
    """Verify that GET /metrics includes ETL counters and gauges."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        text = resp.text

        assert "etl_runs_total" in text
        assert "etl_records_processed_total" in text
        assert "etl_records_failed_total" in text
        assert "etl_duration_seconds" in text
        assert "etl_last_success_timestamp" in text
