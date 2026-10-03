"""Model Management Service (Fase 6.22).

Handles model lifecycle management: promotion across development/staging/production,
automated rollback with active production invariant, and full provenance/lineage retrieval.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models.knowledge import DatasetVersion, ModelVersion
from app.nlp.contracts import (
    ModelLifecycleState,
    ModelLineage,
    PromotionResult,
    RollbackResult,
    validate_model_transition,
)
from app.repositories.knowledge import ModelRepository


class ModelManagementService:
    """Application service for managing machine learning model lifecycle and versioning."""

    def __init__(self, model_repo: ModelRepository) -> None:
        self._repo = model_repo

    async def get_model(self, model_id: uuid.UUID) -> ModelVersion | None:
        return await self._repo.get(model_id)

    async def get_by_version(self, name: str, version: str) -> ModelVersion | None:
        return await self._repo.get_by_version(name, version)

    async def get_active_model(
        self, kind: str = "classifier", preferred_status: str = "production"
    ) -> ModelVersion | None:
        return await self._repo.get_active_model(kind=kind, preferred_status=preferred_status)

    async def list_models(
        self, kind: str | None = None, status: str | None = None
    ) -> list[ModelVersion]:
        return await self._repo.list_models(kind=kind, status=status)

    async def list_dataset_versions(self) -> list[DatasetVersion]:
        return await self._repo.list_dataset_versions()

    async def promote_model(
        self, model_id: uuid.UUID, target_status: str | ModelLifecycleState
    ) -> PromotionResult:
        """Promote a model to a target status (draft, staging, production, archived).

        If promoted to 'production', any previous production model of the same kind
        is automatically demoted to 'staging'.
        """
        target_str = target_status.value if isinstance(target_status, ModelLifecycleState) else str(target_status)
        model = await self._repo.get(model_id)
        if model is None:
            raise ValueError(f"ModelVersion '{model_id}' no encontrado")

        prev_status = model.status
        promoted, demoted = await self._repo.promote(model_id, target_str)

        return PromotionResult(
            model_id=str(promoted.id),
            name=promoted.name,
            version=promoted.version,
            previous_status=prev_status,
            new_status=promoted.status,
            demoted_model_id=str(demoted.id) if demoted else None,
            demoted_version=demoted.version if demoted else None,
        )

    async def rollback_model(self, kind: str = "classifier") -> RollbackResult:
        """Rollback the active production model to the latest staging version."""
        promoted_candidate, demoted_prod = await self._repo.rollback(kind=kind)

        return RollbackResult(
            demoted_model_id=str(demoted_prod.id),
            demoted_version=demoted_prod.version,
            promoted_model_id=str(promoted_candidate.id),
            promoted_version=promoted_candidate.version,
            status=promoted_candidate.status,
        )

    async def get_model_lineage(self, model_id: uuid.UUID) -> ModelLineage | None:
        """Retrieve full training provenance, dataset version, hyperparameters, metrics, and inference usage."""
        data = await self._repo.get_model_lineage(model_id)
        if data is None:
            return None

        return ModelLineage(
            model_id=data["model_id"],
            name=data["name"],
            version=data["version"],
            kind=data["kind"],
            status=data["status"],
            artifact_uri=data["artifact_uri"],
            dataset_version_id=data["dataset_version_id"],
            dataset_name=data["dataset_name"],
            dataset_version=data["dataset_version"],
            dataset_record_count=data["dataset_record_count"],
            hyperparameters=data["hyperparameters"],
            metrics=data["metrics"],
            trained_at=data["trained_at"],
            predictions_count=data["predictions_count"],
        )
