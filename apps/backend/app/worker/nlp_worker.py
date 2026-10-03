"""Executable entry point to run the NLP Celery worker process (Fase 6.20)."""

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_worker() -> None:
    """Run Celery worker listening explicitly on the 'nlp' queue."""
    settings = get_settings()
    logger.info("Starting NLP Celery Worker for environment=%s...", settings.environment)
    worker = celery_app.Worker(
        queues=["nlp"],
        concurrency=2,
        loglevel="INFO",
        traceback=True,
    )
    worker.start()


if __name__ == "__main__":
    run_worker()
