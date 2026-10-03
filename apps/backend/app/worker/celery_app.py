from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "market_insight",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


# Apply the centralized ETL orchestration configuration (routes, beat schedule,
# retry policy). Import is deferred to avoid a circular import with the
# scheduler module, which in turn imports this module.
def _apply_etl_configuration() -> None:
    from app.etl.orchestration.scheduler import configure_celery

    configure_celery()


_apply_etl_configuration()
celery_app.conf.include = ["app.worker.nlp_tasks", "app.etl.orchestration.jobs"]
celery_app.conf.task_routes.update({"app.worker.nlp_tasks.*": {"queue": "nlp"}})

# Registers the signal handlers: request-id propagation and worker logs/errors/metrics.
from app.worker import observability, tracing  # noqa: E402,F401
