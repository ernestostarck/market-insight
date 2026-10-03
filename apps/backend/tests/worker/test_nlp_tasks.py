"""Unit tests for the NLP asynchronous worker and job tracker (Fase 6.20)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.knowledge import NLPJob
from app.nlp.contracts import JobError, JobResult, JobStatus, PipelineStage
from app.repositories.knowledge import NLPJobRepository
from app.worker.job_tracker import JobTracker
from app.worker.nlp_tasks import process_nlp_batch, process_nlp_job


def test_job_tracker_with_mock_redis() -> None:
    mock_redis = MagicMock()
    tracker = JobTracker(redis_client=mock_redis)

    # Idempotency miss & hit
    mock_redis.get.return_value = None
    assert tracker.get_idempotent_result("key1") is None

    mock_redis.get.return_value = json.dumps({"status": "succeeded", "result": {"foo": "bar"}})
    hit = tracker.get_idempotent_result("key1")
    assert hit is not None
    assert hit["result"] == {"foo": "bar"}

    # Record job start
    tracker.record_job_start("task-123", "key1", 42)
    assert mock_redis.set.called

    # Record success
    tracker.record_job_success("task-123", "key1", {"status": "ok"}, duration_seconds=1.23)
    assert mock_redis.set.call_count >= 2

    # Record failure
    tracker.record_job_failure("task-123", "key1", {"code": "err"}, duration_seconds=0.45)
    assert mock_redis.set.called

    # Get job state
    mock_redis.get.return_value = json.dumps({"status": "running"})
    state = tracker.get_job_state("task-123")
    assert state == {"status": "running"}


def test_job_tracker_fallback_when_none() -> None:
    tracker = JobTracker(redis_client=None)
    tracker._redis = None

    assert tracker.get_idempotent_result("any") is None
    assert tracker.get_job_state("any") is None
    # No exceptions raised on writes
    tracker.record_job_start("task-1", "key-1", 1)
    tracker.record_job_success("task-1", "key-1", {}, 1.0)
    tracker.record_job_failure("task-1", "key-1", {}, 1.0)


def test_process_nlp_job_success() -> None:
    payload = {
        "licitacion_id": 100,
        "text_hash": "a" * 64,
        "versions": {
            "taxonomy": "taxonomy-2026.2",
            "semantic_dictionary": "dictionary-2026.1",
            "model": None,
            "embedding_model": None,
        },
    }

    mock_result = JobResult(
        job_key="100:" + "a" * 64 + ":taxonomy-2026.2:dictionary-2026.1:none:none",
        licitacion_id=100,
        completed_stages=(PipelineStage.CLASSIFICATION, PipelineStage.EMBEDDINGS),
        pending_stages=(),
        status=JobStatus.SUCCEEDED,
    )
    process_nlp_job.request.id = "task-uuid-1"
    process_nlp_job.request.retries = 0

    with (
        patch("app.worker.nlp_tasks.execute_nlp_job", return_value=mock_result),
        patch("app.worker.nlp_tasks._job_tracker") as mock_tracker,
        patch("app.worker.nlp_tasks._db_record_job_start"),
        patch("app.worker.nlp_tasks._db_record_job_finish"),
    ):
        mock_tracker.get_idempotent_result.return_value = None

        res = process_nlp_job(payload)
        assert res["status"] == "succeeded"
        assert mock_tracker.record_job_start.called
        assert mock_tracker.record_job_success.called


def test_process_nlp_job_idempotent_hit() -> None:
    payload = {
        "licitacion_id": 100,
        "text_hash": "b" * 64,
        "versions": {
            "taxonomy": "taxonomy-2026.2",
            "semantic_dictionary": "dictionary-2026.1",
            "model": None,
            "embedding_model": None,
        },
    }

    process_nlp_job.request.id = "task-uuid-2"

    with (
        patch("app.worker.nlp_tasks.execute_nlp_job") as mock_exec,
        patch("app.worker.nlp_tasks._job_tracker") as mock_tracker,
    ):
        mock_tracker.get_idempotent_result.return_value = {
            "status": "succeeded",
            "result": {"status": "succeeded", "cached": True},
        }

        res = process_nlp_job(payload)
        assert res["cached"] is True
        # Pipeline execution was skipped
        assert not mock_exec.called


def test_process_nlp_job_failure() -> None:
    payload = {
        "licitacion_id": 101,
        "text_hash": "c" * 64,
        "versions": {
            "taxonomy": "taxonomy-2026.2",
            "semantic_dictionary": "dictionary-2026.1",
            "model": None,
            "embedding_model": None,
        },
    }

    mock_failed_result = JobResult(
        job_key="key-fail",
        licitacion_id=101,
        completed_stages=(),
        pending_stages=(PipelineStage.CLASSIFICATION,),
        status=JobStatus.FAILED,
        error=JobError(PipelineStage.CLASSIFICATION, "stage_err", "Classification failed"),
    )

    process_nlp_job.request.id = "task-uuid-3"
    process_nlp_job.request.retries = 0

    with (
        patch("app.worker.nlp_tasks.execute_nlp_job", return_value=mock_failed_result),
        patch("app.worker.nlp_tasks._job_tracker") as mock_tracker,
        patch("app.worker.nlp_tasks._db_record_job_start"),
        patch("app.worker.nlp_tasks._db_record_job_finish"),
    ):
        mock_tracker.get_idempotent_result.return_value = None

        res = process_nlp_job(payload)
        assert res["status"] == "failed"
        assert mock_tracker.record_job_failure.called


def test_process_nlp_batch() -> None:
    payloads = [
        {"licitacion_id": 1},
        {"licitacion_id": 2},
    ]

    with patch("app.worker.nlp_tasks.process_nlp_job") as mock_single:
        mock_single.side_effect = [
            {"licitacion_id": 1, "status": "succeeded"},
            {"licitacion_id": 2, "status": "failed"},
        ]

        batch_res = process_nlp_batch(payloads)
        assert batch_res["total"] == 2
        assert batch_res["succeeded"] == 1
        assert batch_res["failed"] == 1
        assert "duration_seconds" in batch_res
        assert len(batch_res["results"]) == 2


@pytest.mark.asyncio
async def test_nlp_job_repository() -> None:
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo = NLPJobRepository(mock_session)

    test_job = NLPJob(
        id=uuid.uuid4(),
        celery_task_id="celery-1",
        idempotency_key="key-1",
        licitacion_id=55,
        status="queued",
    )

    # Create
    created = await repo.create(test_job)
    assert created.licitacion_id == 55
    assert mock_session.add.called
    assert mock_session.flush.called

    # Get by id
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = test_job
    mock_session.execute.return_value = mock_result

    fetched = await repo.get_by_id(test_job.id)
    assert fetched == test_job

    # Get by celery task id
    by_task = await repo.get_by_celery_task_id("celery-1")
    assert by_task == test_job

    # Get by idempotency key
    by_key = await repo.get_by_idempotency_key("key-1")
    assert by_key == test_job

    # List by licitacion
    mock_result.scalars().all.return_value = [test_job]
    listed = await repo.list_by_licitacion_id(55)
    assert len(listed) == 1

    # Update status
    updated = await repo.update_status(
        test_job.id,
        status="succeeded",
        duration_seconds=2.5,
        completed_stages=["classification"],
        result_summary={"ok": True},
    )
    assert updated is not None
    assert updated.status == "succeeded"
    assert updated.duration_seconds == 2.5
