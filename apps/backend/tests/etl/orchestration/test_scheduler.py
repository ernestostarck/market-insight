"""Tests for the ETL beat scheduler (Fase 3.11)."""

from __future__ import annotations

from app.etl.orchestration.scheduler import build_beat_schedule


class TestBuildBeatSchedule:
    def test_schedule_has_sync_all_entry(self) -> None:
        schedule = build_beat_schedule()

        assert "sync-all" in schedule
        assert schedule["sync-all"]["task"] == "app.etl.orchestration.jobs.sync_all"

    def test_schedule_creates_per_resource_entries(self) -> None:
        resources = ("licitaciones", "contratos")
        schedule = build_beat_schedule(resources=resources)

        assert "sync-licitaciones" in schedule
        assert "sync-contratos" in schedule
        assert (
            schedule["sync-licitaciones"]["task"]
            == "app.etl.orchestration.jobs.sync_resource"
        )
        assert schedule["sync-licitaciones"]["args"] == ("licitaciones",)

    def test_schedule_uses_custom_interval(self) -> None:
        schedule = build_beat_schedule(interval_minutes=30)

        assert "sync-licitaciones" in schedule
        entry = schedule["sync-licitaciones"]["schedule"]

        # Celery wraps int intervals as a timedelta.
        assert entry.total_seconds() == 30 * 60

    def test_schedule_entries_target_etl_queue(self) -> None:
        schedule = build_beat_schedule(resources=("empresas",))

        assert schedule["sync-empresas"]["options"]["queue"] == "market-insight"
