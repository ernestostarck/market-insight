"""Asynchronous worker entrypoint for the NLP pipeline (Fase 6.20)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from io import BytesIO
from typing import Any

import joblib
from minio import Minio
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.infrastructure.storage.minio_storage import MinioObjectStorage
from app.ml.embeddings import EmbeddingService
from app.nlp.classification import ClassificationStageExecutor
from app.nlp.classifier_training_db import latest_production_or_staging_classifier
from app.nlp.contracts import JobStatus, NLPJobRequest, PipelineStage
from app.nlp.knowledge_stage import KnowledgeStageExecutor
from app.nlp.observability.metrics import (
    NLP_ERRORS_TOTAL,
    NLP_PROCESSING_DURATION_SECONDS,
    NLP_TENDERS_PROCESSED_TOTAL,
)
from app.nlp.semantic import EmbeddingsStageExecutor
from app.nlp.stages import StageRegistry, execute_nlp_job
from app.worker.celery_app import celery_app
from app.worker.job_tracker import JobTracker

logger = logging.getLogger(__name__)

# One engine for the whole worker process (matches app/etl/orchestration/jobs.py's
# _pipeline_factory pattern) — connections are opened per stage run, not per job.
_engine = create_engine(get_settings().database_url, pool_pre_ping=True)
_job_tracker = JobTracker()


def _load_classifier() -> tuple[object | None, uuid.UUID | None, uuid.UUID | None]:
    """Loads the supervised classifier (6.14) the same way at worker
    startup as the embedding model — paid once, not per job. Returns
    (None, None, None) when no classifier has been trained yet (the
    pipeline still runs fine with rules+semantic only, see 6.15)."""
    try:
        with _engine.connect() as connection:
            record = latest_production_or_staging_classifier(connection)
        if record is None:
            return None, None, None

        bucket, object_name = record["artifact_uri"].removeprefix("s3://").split("/", 1)
        client = Minio(
            endpoint=get_settings().minio_endpoint,
            access_key=get_settings().minio_access_key,
            secret_key=get_settings().minio_secret_key,
            secure=False,
        )
        payload = MinioObjectStorage(client).download(bucket, object_name)
        classifier = joblib.load(BytesIO(payload))

        dataset_version_id = None
        raw_dataset_version_id = (record["parameters"] or {}).get("dataset_version_id")
        if raw_dataset_version_id:
            dataset_version_id = uuid.UUID(raw_dataset_version_id)

        logger.info("loaded classifier model_version_id=%s for the NLP worker", record["id"])
        return classifier, record["id"], dataset_version_id
    except Exception as exc:
        logger.warning("Could not load classifier artifact: %s", exc)
        return None, None, None


_classifier, _classifier_model_version_id, _classifier_dataset_version_id = _load_classifier()

STAGE_REGISTRY = StageRegistry({
    PipelineStage.CLASSIFICATION: ClassificationStageExecutor(lambda: _engine.connect()),
    PipelineStage.EMBEDDINGS: EmbeddingsStageExecutor(
        lambda: _engine.connect(),
        EmbeddingService(),
        classifier=_classifier,
        classifier_model_version_id=_classifier_model_version_id,
        classifier_dataset_version_id=_classifier_dataset_version_id,
    ),
    PipelineStage.KNOWLEDGE: KnowledgeStageExecutor(lambda: _engine.connect()),
})


def _db_get_idempotent_job(idempotency_key: str) -> dict[str, Any] | None:
    try:
        with _engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, status, duration_seconds, completed_stages, pending_stages, result_summary "
                    "FROM knowledge.nlp_jobs WHERE idempotency_key = :key AND status = 'succeeded' LIMIT 1"
                ),
                {"key": idempotency_key},
            ).mappings().first()
            if row:
                return dict(row)
    except Exception as exc:
        logger.warning("DB read error checking idempotency '%s': %s", idempotency_key, exc)
    return None


def _db_record_job_start(task_id: str, idempotency_key: str, licitacion_id: int) -> None:
    try:
        with _engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO knowledge.nlp_jobs (id, celery_task_id, idempotency_key, licitacion_id, status, created_at, updated_at)
                    VALUES (:id, :task_id, :idempotency_key, :licitacion_id, 'running', now(), now())
                    ON CONFLICT (idempotency_key) DO UPDATE
                    SET celery_task_id = EXCLUDED.celery_task_id, status = 'running', updated_at = now()
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "task_id": task_id,
                    "idempotency_key": idempotency_key,
                    "licitacion_id": licitacion_id,
                },
            )
    except Exception as exc:
        logger.warning("DB write error recording job start '%s': %s", task_id, exc)


def _db_record_job_finish(
    idempotency_key: str,
    status: str,
    duration_seconds: float,
    completed_stages: list[str] | None = None,
    pending_stages: list[str] | None = None,
    error: dict[str, Any] | None = None,
    result_summary: dict[str, Any] | None = None,
    retries: int = 0,
) -> None:
    try:
        with _engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE knowledge.nlp_jobs
                    SET status = :status,
                        duration_seconds = :duration_seconds,
                        completed_stages = :completed_stages,
                        pending_stages = :pending_stages,
                        error = :error,
                        result_summary = :result_summary,
                        retries = :retries,
                        updated_at = now()
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {
                    "idempotency_key": idempotency_key,
                    "status": status,
                    "duration_seconds": duration_seconds,
                    "completed_stages": json.dumps(completed_stages) if completed_stages is not None else None,
                    "pending_stages": json.dumps(pending_stages) if pending_stages is not None else None,
                    "error": json.dumps(error) if error is not None else None,
                    "result_summary": json.dumps(result_summary) if result_summary is not None else None,
                    "retries": retries,
                },
            )
    except Exception as exc:
        logger.warning("DB write error recording job finish for '%s': %s", idempotency_key, exc)


@celery_app.task(
    name="app.worker.nlp_tasks.process_nlp_job",
    bind=True,
    acks_late=True,
    max_retries=3,
    default_retry_delay=5,
)
def process_nlp_job(self: Any, payload: dict[str, object]) -> dict[str, object]:
    """Execute asynchronous NLP pipeline stages for a single tender with idempotency,
    retries and telemetry."""
    job = NLPJobRequest.from_payload(payload)
    task_id = str(getattr(self.request, "id", None) or uuid.uuid4())
    idempotency_key = job.idempotency_key

    # 1. Check idempotency in Redis cache
    cached = _job_tracker.get_idempotent_result(idempotency_key)
    if cached and cached.get("result"):
        logger.info("Idempotent hit in Redis for job key %s", idempotency_key)
        return cached["result"]

    # 2. Check idempotency in DB
    db_job = _db_get_idempotent_job(idempotency_key)
    if db_job and db_job.get("result_summary"):
        logger.info("Idempotent hit in PostgreSQL for job key %s", idempotency_key)
        return db_job["result_summary"]

    # 3. Record start
    _job_tracker.record_job_start(task_id, idempotency_key, job.licitacion_id)
    _db_record_job_start(task_id, idempotency_key, job.licitacion_id)

    start_time = time.perf_counter()
    retries = getattr(self.request, "retries", 0)

    try:
        # 4. Execute pipeline stages
        job_result = execute_nlp_job(job, STAGE_REGISTRY)
        duration = round(time.perf_counter() - start_time, 4)
        result_payload = job_result.to_payload()

        if job_result.status == JobStatus.FAILED:
            err_dict = job_result.error.to_payload() if job_result.error else {"code": "unknown", "message": "error"}
            NLP_TENDERS_PROCESSED_TOTAL.labels(stage="pipeline", status="failed").inc()
            NLP_ERRORS_TOTAL.labels(
                stage=str(job_result.error.stage.value if job_result.error else "pipeline"),
                error_code=str(err_dict.get("code", "unknown")),
            ).inc()
            _job_tracker.record_job_failure(task_id, idempotency_key, err_dict, duration)
            _db_record_job_finish(
                idempotency_key=idempotency_key,
                status="failed",
                duration_seconds=duration,
                completed_stages=[s.value for s in job_result.completed_stages],
                pending_stages=[s.value for s in job_result.pending_stages],
                error=err_dict,
                result_summary=result_payload,
                retries=retries,
            )
        else:
            NLP_TENDERS_PROCESSED_TOTAL.labels(stage="pipeline", status="succeeded").inc()
            NLP_PROCESSING_DURATION_SECONDS.labels(stage="pipeline").observe(duration)
            _job_tracker.record_job_success(task_id, idempotency_key, result_payload, duration)
            _db_record_job_finish(
                idempotency_key=idempotency_key,
                status="succeeded",
                duration_seconds=duration,
                completed_stages=[s.value for s in job_result.completed_stages],
                pending_stages=[s.value for s in job_result.pending_stages],
                result_summary=result_payload,
                retries=retries,
            )

        return result_payload

    except Exception as exc:
        duration = round(time.perf_counter() - start_time, 4)
        err_dict = {"stage": "runtime", "code": exc.__class__.__name__, "message": str(exc)}
        NLP_TENDERS_PROCESSED_TOTAL.labels(stage="pipeline", status="error").inc()
        NLP_ERRORS_TOTAL.labels(stage="runtime", error_code=exc.__class__.__name__).inc()
        _job_tracker.record_job_failure(task_id, idempotency_key, err_dict, duration)
        _db_record_job_finish(
            idempotency_key=idempotency_key,
            status="failed",
            duration_seconds=duration,
            error=err_dict,
            retries=retries,
        )

        # Retry transient exceptions if configured
        if retries < getattr(self, "max_retries", 3):
            countdown = 2 ** retries
            logger.warning("Retrying NLP job %s (attempt %s) in %ss: %s", task_id, retries + 1, countdown, exc)
            raise self.retry(exc=exc, countdown=countdown)

        raise exc


@celery_app.task(name="app.worker.nlp_tasks.process_nlp_batch", bind=True)
def process_nlp_batch(self: Any, payloads: list[dict[str, object]]) -> dict[str, object]:
    """Execute or coordinate a batch of NLP jobs with aggregated metrics."""
    batch_start = time.perf_counter()
    succeeded_count = 0
    failed_count = 0
    results: list[dict[str, object]] = []

    for item in payloads:
        try:
            res = process_nlp_job(item)
            results.append(res)
            if res.get("status") == "failed":
                failed_count += 1
            else:
                succeeded_count += 1
        except Exception as exc:
            failed_count += 1
            results.append({
                "licitacion_id": item.get("licitacion_id"),
                "status": "failed",
                "error": {"code": exc.__class__.__name__, "message": str(exc)},
            })

    total_duration = round(time.perf_counter() - batch_start, 4)
    return {
        "total": len(payloads),
        "succeeded": succeeded_count,
        "failed": failed_count,
        "duration_seconds": total_duration,
        "results": results,
    }
