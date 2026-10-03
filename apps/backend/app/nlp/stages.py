"""Per-stage execution contract for the asynchronous NLP worker.

`app/worker/nlp_tasks.py` should stay a thin composition root: it resolves a
payload into an `NLPJobRequest` and calls `execute_nlp_job`. Later subphases
(6.6+) register one `StageExecutor` per stage on `STAGE_REGISTRY` instead of
editing the Celery task itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from app.nlp.contracts import (
    ASYNC_STAGES, ArtifactVersions, JobError, JobResult, JobStatus, NLPJobRequest, PipelineStage,
)


@dataclass(frozen=True, slots=True)
class StageContext:
    """Immutable input available to every async stage executor."""

    licitacion_id: int
    text_hash: str
    versions: ArtifactVersions


@dataclass(frozen=True, slots=True)
class StageOutcome:
    stage: PipelineStage
    ok: bool


class StageExecutor(Protocol):
    def run(self, context: StageContext) -> bool: ...


class StageRegistry:
    """Ordered, pluggable set of stage executors keyed by `PipelineStage`."""

    def __init__(self, executors: Mapping[PipelineStage, StageExecutor] | None = None) -> None:
        self._executors: dict[PipelineStage, StageExecutor] = dict(executors or {})

    def run(self, stages: Iterable[PipelineStage], context: StageContext) -> tuple[StageOutcome, ...]:
        """Run registered executors in order, stopping at the first failure.

        Classification -> Embeddings -> Knowledge are sequentially dependent
        (docs/07-ai/architecture.md), so a failed stage must not let a later
        stage run against an incomplete result. Stages without a registered
        executor, and stages after a failure, are simply not attempted.
        """
        outcomes: list[StageOutcome] = []
        for stage in stages:
            executor = self._executors.get(stage)
            if executor is None:
                continue
            ok = executor.run(context)
            outcomes.append(StageOutcome(stage=stage, ok=ok))
            if not ok:
                break
        return tuple(outcomes)


def execute_nlp_job(job: NLPJobRequest, registry: StageRegistry) -> JobResult:
    """Pure orchestration for one job's `ASYNC_STAGES` — testable without Celery."""
    context = StageContext(job.licitacion_id, job.text_hash, job.versions)
    ordered_stages = tuple(sorted(ASYNC_STAGES, key=str))
    outcomes = registry.run(ordered_stages, context)

    attempted = {outcome.stage for outcome in outcomes}
    completed = tuple(outcome.stage for outcome in outcomes if outcome.ok)
    failed = next((outcome for outcome in outcomes if not outcome.ok), None)
    pending = tuple(stage for stage in ordered_stages if stage not in attempted)

    if failed is not None:
        return JobResult(
            job_key=job.idempotency_key, licitacion_id=job.licitacion_id,
            completed_stages=completed, pending_stages=pending, status=JobStatus.FAILED,
            error=JobError(failed.stage, "stage_failed", f"stage {failed.stage.value} reported failure"),
        )
    status = JobStatus.PARTIAL if pending else JobStatus.SUCCEEDED
    return JobResult(
        job_key=job.idempotency_key, licitacion_id=job.licitacion_id,
        completed_stages=completed, pending_stages=pending, status=status,
    )
