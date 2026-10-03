"""Celery tasks for the ETL worker (Fase 3.11).

The actual job logic lives in :mod:`app.etl.orchestration.jobs`; this module
keeps a legacy-compatible entrypoint (``sync_tenders``) so that existing
callers and the ``worker`` container keep working unchanged.
"""

from __future__ import annotations

from app.etl.orchestration.jobs import DEFAULT_RESOURCES
from app.worker.celery_app import celery_app

#: Fully-qualified task names for the centralized orchestration layer.
_SYNC_ALL_TASK = "app.etl.orchestration.jobs.sync_all"


@celery_app.task(name="app.worker.tasks.sync_tenders")
def sync_tenders() -> dict[str, object]:
    """Legacy-compatible alias that delegates to the 3.11 orchestration jobs.

    Enqueues a full refresh through the centralized orchestration layer. The
    real worker entrypoints are the ``app.etl.orchestration.jobs.*`` tasks.
    """
    celery_app.send_task(
        _SYNC_ALL_TASK,
        kwargs={"source": "chilecompra_api"},
    )
    return {
        "status": "queued",
        "resources": list(DEFAULT_RESOURCES),
    }


__all__ = [
    "sync_tenders",
    "DEFAULT_RESOURCES",
]
