"""Celery beat scheduling for the ETL pipeline (Fase 3.11).

Centralizes the periodic schedule used by ``celery beat`` so incremental loads
run outside the FastAPI process. The schedule is declarative and easy to tune
per resource (interval, queue, retry policy).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from celery.schedules import crontab

from app.worker.celery_app import celery_app

#: Default queue for ETL jobs.
ETL_QUEUE = "market-insight"

#: Per-resource sync cadence (in minutes). Tune per stream.
DEFAULT_SYNC_INTERVAL_MINUTES = 60


def build_beat_schedule(
    *,
    resources: tuple[str, ...] | None = None,
    interval_minutes: int = DEFAULT_SYNC_INTERVAL_MINUTES,
) -> dict[str, dict[str, Any]]:
    """Return a ``beat_schedule`` mapping resource jobs to periodic tasks.

    Each entry enqueues :func:`app.etl.orchestration.jobs.sync_resource` for a
    given resource on the ETL queue. A single ``sync_all`` entry is also added
    as a convenience for a full refresh.
    """
    targets = resources or (
        "licitaciones",
        "ordenes_compra",
        "empresas",
        "contratos",
        "convenios_marco",
        "adjudicaciones",
    )

    schedule: dict[str, dict[str, Any]] = {}
    for resource in targets:
        schedule[f"sync-{resource}"] = {
            "task": "app.etl.orchestration.jobs.sync_resource",
            "schedule": timedelta(minutes=interval_minutes),
            "args": (resource,),
            "options": {"queue": ETL_QUEUE},
        }

    schedule["sync-all"] = {
        "task": "app.etl.orchestration.jobs.sync_all",
        "schedule": crontab(minute=0, hour=3),  # daily 03:00
        "options": {"queue": ETL_QUEUE},
    }
    return schedule


def configure_celery(
    *,
    resources: tuple[str, ...] | None = None,
    interval_minutes: int = DEFAULT_SYNC_INTERVAL_MINUTES,
    result_expires: int = 3600 * 24,
    task_acks_late: bool = True,
) -> Any:
    """Configure the global Celery app with routes, beat schedule and settings.

    Call this once at process startup (e.g. from ``worker`` entrypoint) to wire
    the schedule and routing. Returns the imported ``celery_app`` for chaining.
    """
    schedule = build_beat_schedule(
        resources=resources,
        interval_minutes=interval_minutes,
    )
    celery_app.conf.beat_schedule = schedule
    celery_app.conf.task_routes = {
        "app.etl.orchestration.jobs.*": {"queue": ETL_QUEUE},
    }
    celery_app.conf.task_acks_late = task_acks_late
    celery_app.conf.result_expires = result_expires
    celery_app.conf.worker_prefetch_multiplier = 1
    return celery_app


__all__ = [
    "ETL_QUEUE",
    "DEFAULT_SYNC_INTERVAL_MINUTES",
    "build_beat_schedule",
    "configure_celery",
]
