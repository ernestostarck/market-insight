from __future__ import annotations

import pytest
from app.etl.models import ETLMetrics
from app.etl.quality.metrics import metrics_from_etl, quality_rate


def test_quality_rate_basic() -> None:
    assert quality_rate(99, 100) == 0.99
    assert quality_rate(50, 200) == 0.25
    assert quality_rate(0, 10) == 0.0


def test_quality_rate_zero_received_returns_none() -> None:
    assert quality_rate(0, 0) is None
    assert quality_rate(5, 0) is None


def test_quality_rate_rounds_to_six_decimals() -> None:
    # 1/3 = 0.333333...
    assert quality_rate(1, 3) == 0.333333
    assert isinstance(quality_rate(1, 3), float)


def test_metrics_from_etl_maps_counters() -> None:
    metrics = ETLMetrics(
        extracted=200,
        raw_stored=150,
        valid=100,
        invalid=50,
        transformed=100,
        inserted=40,
        updated=30,
        unchanged=20,
        failed=10,
    )

    q = metrics_from_etl(metrics)

    assert q.received == 150  # valid + invalid
    assert q.valid == 100
    assert q.invalid == 50
    assert q.inserted == 40
    assert q.updated == 30
    assert q.duplicates == 20
    assert q.errors == 60  # invalid + failed
    assert q.quality_rate == pytest.approx(100 / 150)


def test_metrics_from_etl_zero_records_has_none_rate() -> None:
    q = metrics_from_etl(ETLMetrics())

    assert q.received == 0
    assert q.quality_rate is None


def test_metrics_from_etl_carries_run_context() -> None:
    q = metrics_from_etl(
        ETLMetrics(valid=10, invalid=0),
        source="chilecompra_api",
        resource="adjudicaciones",
        ingestion_run_id="ETL-20260806-1",
    )

    assert q.source == "chilecompra_api"
    assert q.resource == "adjudicaciones"
    assert q.ingestion_run_id == "ETL-20260806-1"


def test_quality_metrics_to_dict_shape() -> None:
    q = metrics_from_etl(ETLMetrics(valid=10, invalid=0), source="s")
    d = q.to_dict()

    assert d["received"] == 10
    assert d["quality_rate"] == 1.0
    assert "extracted" in d  # extra
    assert d["source"] == "s"
