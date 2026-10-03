"""Stable contracts that connect the API, worker and NLP persistence layers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PipelineStage(StrEnum):
    """Phases of the persisted, asynchronous job pipeline only.

    The synchronous rule preview (`NLPService.classify_by_rules`, `POST /classify`)
    is not a pipeline stage: it never persists and never goes through
    `NLPJobRequest`. See ADR 0002 for why a `RULES` member was rejected.
    """

    PREPROCESSING = "preprocessing"
    NLP = "nlp"
    CLASSIFICATION = "classification"
    EMBEDDINGS = "embeddings"
    KNOWLEDGE = "knowledge"


class ProcessingMode(StrEnum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"


@dataclass(frozen=True, slots=True)
class ArtifactVersions:
    """Immutable versions that make a prediction reproducible."""

    taxonomy: str
    semantic_dictionary: str
    model: str | None = None
    embedding_model: str | None = None


@dataclass(frozen=True, slots=True)
class NLPJobRequest:
    """Message sent from the API to the asynchronous NLP worker."""

    licitacion_id: int
    text_hash: str
    versions: ArtifactVersions

    @property
    def idempotency_key(self) -> str:
        return ":".join((
            str(self.licitacion_id), self.text_hash, self.versions.taxonomy,
            self.versions.semantic_dictionary, self.versions.model or "none",
            self.versions.embedding_model or "none",
        ))

    def to_payload(self) -> dict[str, object]:
        return {
            "licitacion_id": self.licitacion_id,
            "text_hash": self.text_hash,
            "versions": {
                "taxonomy": self.versions.taxonomy,
                "semantic_dictionary": self.versions.semantic_dictionary,
                "model": self.versions.model,
                "embedding_model": self.versions.embedding_model,
            },
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "NLPJobRequest":
        versions = payload["versions"]
        if not isinstance(versions, dict):
            raise ValueError("versions must be an object")
        return cls(
            licitacion_id=int(payload["licitacion_id"]),
            text_hash=str(payload["text_hash"]),
            versions=ArtifactVersions(
                taxonomy=str(versions["taxonomy"]),
                semantic_dictionary=str(versions["semantic_dictionary"]),
                model=str(versions["model"]) if versions.get("model") else None,
                embedding_model=str(versions["embedding_model"]) if versions.get("embedding_model") else None,
            ),
        )


SYNC_STAGES = frozenset({PipelineStage.PREPROCESSING, PipelineStage.NLP})
ASYNC_STAGES = frozenset({
    PipelineStage.CLASSIFICATION,
    PipelineStage.EMBEDDINGS,
    PipelineStage.KNOWLEDGE,
})


def processing_mode(stage: PipelineStage) -> ProcessingMode:
    """Keep expensive or persistent work out of the request-response path."""
    return ProcessingMode.SYNCHRONOUS if stage in SYNC_STAGES else ProcessingMode.ASYNCHRONOUS


class JobStatus(StrEnum):
    """Progress of an `NLPJobRequest` through `ASYNC_STAGES`.

    Deliberately does not mirror Celery's own task states (PENDING/STARTED/RETRY):
    those describe task-queue mechanics, not pipeline-stage completion, which is
    the thing callers actually need to reason about.
    """

    QUEUED = "queued"
    PARTIAL = "partial"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobError:
    stage: PipelineStage
    code: str
    message: str

    def to_payload(self) -> dict[str, object]:
        return {"stage": self.stage.value, "code": self.code, "message": self.message}

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "JobError":
        return cls(
            stage=PipelineStage(str(payload["stage"])),
            code=str(payload["code"]),
            message=str(payload["message"]),
        )


@dataclass(frozen=True, slots=True)
class JobResult:
    """Outcome of executing a job's `ASYNC_STAGES` against a `StageRegistry`."""

    job_key: str
    licitacion_id: int
    completed_stages: tuple[PipelineStage, ...]
    pending_stages: tuple[PipelineStage, ...]
    status: JobStatus
    error: JobError | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "job_key": self.job_key,
            "licitacion_id": self.licitacion_id,
            "completed_stages": [stage.value for stage in self.completed_stages],
            "pending_stages": [stage.value for stage in self.pending_stages],
            "status": self.status.value,
            "error": self.error.to_payload() if self.error else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "JobResult":
        error = payload.get("error")
        return cls(
            job_key=str(payload["job_key"]),
            licitacion_id=int(payload["licitacion_id"]),
            completed_stages=tuple(PipelineStage(value) for value in payload["completed_stages"]),  # type: ignore[union-attr]
            pending_stages=tuple(PipelineStage(value) for value in payload["pending_stages"]),  # type: ignore[union-attr]
            status=JobStatus(str(payload["status"])),
            error=JobError.from_payload(error) if isinstance(error, dict) else None,
        )


class ModelLifecycleState(StrEnum):
    """Promotion states for a `ModelVersion`. See docs/07-ai/model-versioning.md."""

    DRAFT = "draft"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


_ALLOWED_MODEL_TRANSITIONS: dict[ModelLifecycleState, frozenset[ModelLifecycleState]] = {
    ModelLifecycleState.DRAFT: frozenset({ModelLifecycleState.STAGING, ModelLifecycleState.ARCHIVED}),
    ModelLifecycleState.STAGING: frozenset({
        ModelLifecycleState.PRODUCTION, ModelLifecycleState.DRAFT, ModelLifecycleState.ARCHIVED,
    }),
    # PRODUCTION -> STAGING is the rollback demotion path, not a re-evaluation step.
    ModelLifecycleState.PRODUCTION: frozenset({ModelLifecycleState.STAGING, ModelLifecycleState.ARCHIVED}),
    # Terminal: a superseded model is never revived, a new ModelVersion row re-enters at DRAFT.
    ModelLifecycleState.ARCHIVED: frozenset(),
}


def validate_model_transition(current: ModelLifecycleState, target: ModelLifecycleState) -> None:
    if target not in _ALLOWED_MODEL_TRANSITIONS[current]:
        raise ValueError(f"invalid model lifecycle transition: {current} -> {target}")


@dataclass(frozen=True, slots=True)
class DictionaryVersion:
    """Identifies an immutable, append-only semantic dictionary release."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith("dictionary-"):
            raise ValueError(f"semantic dictionary version must start with 'dictionary-': {self.value!r}")


@dataclass(frozen=True, slots=True)
class TaxonomyVersion:
    """Identifies an immutable, versioned hierarchical taxonomy release."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith("taxonomy-"):
            raise ValueError(f"taxonomy version must start with 'taxonomy-': {self.value!r}")


@dataclass(frozen=True, slots=True)
class ModelLineage:
    """Complete provenance and lineage metadata for a trained model."""

    model_id: str
    name: str
    version: str
    kind: str
    status: str
    artifact_uri: str | None
    dataset_version_id: str | None
    dataset_name: str | None
    dataset_version: str | None
    dataset_record_count: int | None
    hyperparameters: dict[str, object]
    metrics: dict[str, object]
    trained_at: str | None
    predictions_count: int = 0


@dataclass(frozen=True, slots=True)
class PromotionResult:
    """Outcome of promoting a model across lifecycle states."""

    model_id: str
    name: str
    version: str
    previous_status: str
    new_status: str
    demoted_model_id: str | None = None
    demoted_version: str | None = None


@dataclass(frozen=True, slots=True)
class RollbackResult:
    """Outcome of rolling back a production model to previous staging/active version."""

    demoted_model_id: str
    demoted_version: str
    promoted_model_id: str
    promoted_version: str
    status: str

