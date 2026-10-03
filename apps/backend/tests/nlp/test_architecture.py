import pytest

from app.nlp.contracts import (
    ASYNC_STAGES,
    SYNC_STAGES,
    ArtifactVersions,
    DictionaryVersion,
    ModelLifecycleState,
    NLPJobRequest,
    PipelineStage,
    ProcessingMode,
    processing_mode,
    validate_model_transition,
)


def test_every_pipeline_stage_has_one_execution_mode() -> None:
    assert SYNC_STAGES.isdisjoint(ASYNC_STAGES)
    assert SYNC_STAGES | ASYNC_STAGES == set(PipelineStage)
    assert processing_mode(PipelineStage.NLP) is ProcessingMode.SYNCHRONOUS
    assert processing_mode(PipelineStage.EMBEDDINGS) is ProcessingMode.ASYNCHRONOUS


def test_worker_job_idempotency_key_tracks_input_and_artifact_versions() -> None:
    versions = ArtifactVersions(
        taxonomy="taxonomy-2026.1", semantic_dictionary="dictionary-2026.1",
        model="classifier-1.0", embedding_model="multilingual-1",
    )
    job = NLPJobRequest(licitacion_id=42, text_hash="abc123", versions=versions)
    assert job.idempotency_key == (
        "42:abc123:taxonomy-2026.1:dictionary-2026.1:classifier-1.0:multilingual-1"
    )


def test_rule_preview_is_not_a_pipeline_stage() -> None:
    stage_values = {stage.value for stage in PipelineStage}
    assert "rule_preview" not in stage_values
    assert "rules" not in stage_values


def test_dictionary_version_requires_prefix() -> None:
    assert DictionaryVersion("dictionary-2026.1").value == "dictionary-2026.1"
    with pytest.raises(ValueError):
        DictionaryVersion("2026.1")


def test_model_lifecycle_promotion_and_rollback_transitions() -> None:
    validate_model_transition(ModelLifecycleState.DRAFT, ModelLifecycleState.STAGING)
    validate_model_transition(ModelLifecycleState.STAGING, ModelLifecycleState.PRODUCTION)
    # Rollback: demote current production, then re-promote a previous staging version.
    validate_model_transition(ModelLifecycleState.PRODUCTION, ModelLifecycleState.STAGING)
    validate_model_transition(ModelLifecycleState.STAGING, ModelLifecycleState.PRODUCTION)

    with pytest.raises(ValueError):
        validate_model_transition(ModelLifecycleState.DRAFT, ModelLifecycleState.PRODUCTION)
    with pytest.raises(ValueError):
        validate_model_transition(ModelLifecycleState.ARCHIVED, ModelLifecycleState.STAGING)
