from app.nlp.contracts import ArtifactVersions, JobResult, JobStatus, NLPJobRequest, PipelineStage
from app.nlp.stages import StageContext, StageRegistry, execute_nlp_job


class _FixedExecutor:
    def __init__(self, ok: bool) -> None:
        self._ok = ok
        self.calls: list[StageContext] = []

    def run(self, context: StageContext) -> bool:
        self.calls.append(context)
        return self._ok


def _job() -> NLPJobRequest:
    return NLPJobRequest(7, "a" * 64, ArtifactVersions("taxonomy-1", "dictionary-1"))


def test_stage_registry_runs_only_registered_stages() -> None:
    executor = _FixedExecutor(ok=True)
    registry = StageRegistry({PipelineStage.CLASSIFICATION: executor})
    context = StageContext(licitacion_id=7, text_hash="a" * 64, versions=ArtifactVersions("taxonomy-1", "dictionary-1"))

    outcomes = registry.run([PipelineStage.CLASSIFICATION, PipelineStage.EMBEDDINGS], context)

    assert [outcome.stage for outcome in outcomes] == [PipelineStage.CLASSIFICATION]
    assert executor.calls == [context]


def test_execute_nlp_job_is_partial_with_empty_registry() -> None:
    result = execute_nlp_job(_job(), StageRegistry())

    assert result.status is JobStatus.PARTIAL
    assert result.completed_stages == ()
    assert result.pending_stages == (PipelineStage.CLASSIFICATION, PipelineStage.EMBEDDINGS, PipelineStage.KNOWLEDGE)


def test_execute_nlp_job_succeeds_when_all_stages_registered_and_ok() -> None:
    registry = StageRegistry({
        PipelineStage.CLASSIFICATION: _FixedExecutor(ok=True),
        PipelineStage.EMBEDDINGS: _FixedExecutor(ok=True),
        PipelineStage.KNOWLEDGE: _FixedExecutor(ok=True),
    })

    result = execute_nlp_job(_job(), registry)

    assert result.status is JobStatus.SUCCEEDED
    assert result.completed_stages == (PipelineStage.CLASSIFICATION, PipelineStage.EMBEDDINGS, PipelineStage.KNOWLEDGE)
    assert result.pending_stages == ()
    assert result.error is None


def test_execute_nlp_job_fails_on_first_failing_stage_and_skips_the_rest() -> None:
    downstream = _FixedExecutor(ok=True)
    registry = StageRegistry({
        PipelineStage.CLASSIFICATION: _FixedExecutor(ok=True),
        PipelineStage.EMBEDDINGS: _FixedExecutor(ok=False),
        PipelineStage.KNOWLEDGE: downstream,
    })

    result = execute_nlp_job(_job(), registry)

    assert result.status is JobStatus.FAILED
    assert result.completed_stages == (PipelineStage.CLASSIFICATION,)
    assert result.pending_stages == (PipelineStage.KNOWLEDGE,)
    assert result.error is not None
    assert result.error.stage is PipelineStage.EMBEDDINGS
    assert downstream.calls == []


def test_job_result_payload_round_trip() -> None:
    registry = StageRegistry({PipelineStage.CLASSIFICATION: _FixedExecutor(ok=False)})

    result = execute_nlp_job(_job(), registry)

    assert JobResult.from_payload(result.to_payload()) == result
