"""Observability for Celery worker processes: structured logs, error tracking and /metrics.

ETL and NLP metrics are incremented inside the workers, not the API, so without
this they were never scraped and never reached Sentry or the JSON log pipeline.

The workers run the ``threads`` pool so every task shares one process (and one
Prometheus registry) with the metrics server started here.
"""

from __future__ import annotations

import logging
import os

from celery.signals import setup_logging, worker_init, worker_ready
from prometheus_client import start_http_server

from app.core.logging import configure_logging
from app.core.sentry import setup_sentry

logger = logging.getLogger(__name__)

METRICS_PORT_ENV = "WORKER_METRICS_PORT"
DEFAULT_METRICS_PORT = 8000

_metrics_server_started = False


@setup_logging.connect
def _configure_worker_logging(**_: object) -> None:
    # Connecting to this signal stops Celery from installing its own log handlers.
    configure_logging()


@worker_init.connect
def _init_error_tracking(**_: object) -> None:
    setup_sentry()


# Also on worker_init: loading the NLP model can take over a minute, and a worker that
# is alive but still loading must not look "down" to Prometheus (NLPWorkerDown, 1 m).
@worker_init.connect
@worker_ready.connect
def _serve_metrics(**_: object) -> None:
    global _metrics_server_started
    port = int(os.environ.get(METRICS_PORT_ENV, DEFAULT_METRICS_PORT))
    if port == 0 or _metrics_server_started:
        return
    start_http_server(port)
    _metrics_server_started = True
    logger.info("Worker metrics served on :%d/metrics", port)
