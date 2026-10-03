"""Unit tests for Data Freshness evaluation service and thresholds."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.monitoring.data_freshness import (
    FRESHNESS_NORMAL_MAX_SECONDS,
    FRESHNESS_WARNING_MAX_SECONDS,
    DataFreshnessReport,
    FreshnessState,
    classify_freshness_state,
    evaluate_data_freshness,
)
from app.monitoring.metrics import DATA_FRESHNESS_SECONDS, ETL_LAST_SUCCESS_TIMESTAMP


def test_classify_freshness_state_none():
    """When no previous data exists, classify as normal."""
    state, msg = classify_freshness_state(None)
    assert state == FreshnessState.NORMAL
    assert "No historical" in msg


def test_classify_freshness_state_normal():
    """Within 18 hours (business day cycle), classify as normal."""
    state, msg = classify_freshness_state(3600.0)  # 1 hour
    assert state == FreshnessState.NORMAL
    assert "up-to-date" in msg

    # Boundary test at 18 hours (64800s)
    state_bound, _ = classify_freshness_state(FRESHNESS_NORMAL_MAX_SECONDS)
    assert state_bound == FreshnessState.NORMAL


def test_classify_freshness_state_warning():
    """Between 18 and 36 hours (minor delays or weekend start), classify as warning."""
    state, msg = classify_freshness_state(FRESHNESS_NORMAL_MAX_SECONDS + 10.0)
    assert state == FreshnessState.WARNING
    assert "degraded" in msg

    # Boundary test at 36 hours (129600s)
    state_bound, _ = classify_freshness_state(FRESHNESS_WARNING_MAX_SECONDS)
    assert state_bound == FreshnessState.WARNING


def test_classify_freshness_state_critical():
    """Exceeding 36 hours, classify as critical."""
    state, msg = classify_freshness_state(FRESHNESS_WARNING_MAX_SECONDS + 1.0)
    assert state == FreshnessState.CRITICAL
    assert "critical" in msg


def test_evaluate_data_freshness_with_db_mock():
    """Evaluate data freshness with mocked database session."""
    mock_db = MagicMock()
    # 2 hours ago
    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
    mock_db.scalar.return_value = two_hours_ago

    report = evaluate_data_freshness(db=mock_db)
    assert isinstance(report, DataFreshnessReport)
    assert report.status == FreshnessState.NORMAL
    assert report.source == "database"
    assert report.freshness_seconds is not None
    assert 7100.0 <= report.freshness_seconds <= 7300.0
    assert report.last_processed_timestamp == two_hours_ago.isoformat()


def test_evaluate_data_freshness_with_etl_metric_fallback():
    """Evaluate data freshness using Prometheus metric fallback when db is None."""
    now_epoch = datetime.now(UTC).timestamp()
    one_day_ago = now_epoch - (24 * 3600)  # 24 hours ago -> WARNING state
    ETL_LAST_SUCCESS_TIMESTAMP.labels(pipeline="licitaciones").set(one_day_ago)

    report = evaluate_data_freshness(db=None)
    assert report.status == FreshnessState.WARNING
    assert report.source == "etl_metrics"
    assert report.freshness_seconds is not None
    assert 86300.0 <= report.freshness_seconds <= 86500.0


def test_evaluate_data_freshness_updates_prometheus_gauge():
    """Ensure evaluate_data_freshness updates DATA_FRESHNESS_SECONDS gauge."""
    mock_db = MagicMock()
    recent = datetime.now(UTC) - timedelta(minutes=30)
    mock_db.scalar.return_value = recent

    report = evaluate_data_freshness(db=mock_db)
    assert report.status == FreshnessState.NORMAL

    # Verify gauge is set
    assert DATA_FRESHNESS_SECONDS._value.get() is not None
