"""Unit tests for Model and Version Management (Fase 6.22)."""

from __future__ import annotations

import dataclasses
import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.dependencies import get_current_user, get_model_management_service
from app.main import app
from app.models.knowledge import DatasetVersion, ModelVersion
from app.models.user import User
from app.nlp.contracts import (
    DictionaryVersion,
    ModelLifecycleState,
    ModelLineage,
    PromotionResult,
    RollbackResult,
    TaxonomyVersion,
    validate_model_transition,
)
from app.repositories.knowledge import ModelRepository
from app.services.nlp.model_management import ModelManagementService


def test_taxonomy_version_validation() -> None:
    valid = TaxonomyVersion("taxonomy-2026.2")
    assert valid.value == "taxonomy-2026.2"

    with pytest.raises(ValueError, match="taxonomy version must start with"):
        TaxonomyVersion("2026.2")


def test_dictionary_version_validation() -> None:
    valid = DictionaryVersion("dictionary-2026.1")
    assert valid.value == "dictionary-2026.1"

    with pytest.raises(ValueError, match="semantic dictionary version must start with"):
        DictionaryVersion("2026.1")


def test_model_lifecycle_transition_validation() -> None:
    # Valid transitions
    validate_model_transition(ModelLifecycleState.DRAFT, ModelLifecycleState.STAGING)
    validate_model_transition(ModelLifecycleState.STAGING, ModelLifecycleState.PRODUCTION)
    validate_model_transition(ModelLifecycleState.PRODUCTION, ModelLifecycleState.STAGING)
    validate_model_transition(ModelLifecycleState.PRODUCTION, ModelLifecycleState.ARCHIVED)

    # Invalid transitions
    with pytest.raises(ValueError, match="invalid model lifecycle transition"):
        validate_model_transition(ModelLifecycleState.DRAFT, ModelLifecycleState.PRODUCTION)

    with pytest.raises(ValueError, match="invalid model lifecycle transition"):
        validate_model_transition(ModelLifecycleState.ARCHIVED, ModelLifecycleState.PRODUCTION)


@pytest.mark.asyncio
async def test_model_management_promote() -> None:
    mock_repo = AsyncMock(spec=ModelRepository)
    service = ModelManagementService(mock_repo)

    model_id = uuid.uuid4()
    candidate_model = ModelVersion(
        id=model_id,
        name="classifier_sgd",
        version="v2.0",
        kind="classifier",
        status="staging",
    )
    old_prod_id = uuid.uuid4()
    old_prod = ModelVersion(
        id=old_prod_id,
        name="classifier_sgd",
        version="v1.0",
        kind="classifier",
        status="staging",
    )

    promoted_model = ModelVersion(
        id=model_id,
        name="classifier_sgd",
        version="v2.0",
        kind="classifier",
        status="production",
    )
    mock_repo.get.return_value = candidate_model
    mock_repo.promote.return_value = (promoted_model, old_prod)

    res = await service.promote_model(model_id, "production")
    assert isinstance(res, PromotionResult)
    assert res.model_id == str(model_id)
    assert res.new_status == "production"
    assert res.demoted_model_id == str(old_prod_id)
    assert res.demoted_version == "v1.0"


@pytest.mark.asyncio
async def test_model_management_rollback() -> None:
    mock_repo = AsyncMock(spec=ModelRepository)
    service = ModelManagementService(mock_repo)

    prod_id = uuid.uuid4()
    staging_id = uuid.uuid4()

    promoted_staging = ModelVersion(
        id=staging_id,
        name="classifier_sgd",
        version="v1.9",
        kind="classifier",
        status="production",
    )
    demoted_prod = ModelVersion(
        id=prod_id,
        name="classifier_sgd",
        version="v2.0",
        kind="classifier",
        status="staging",
    )

    mock_repo.rollback.return_value = (promoted_staging, demoted_prod)

    res = await service.rollback_model("classifier")
    assert isinstance(res, RollbackResult)
    assert res.promoted_model_id == str(staging_id)
    assert res.promoted_version == "v1.9"
    assert res.demoted_model_id == str(prod_id)
    assert res.demoted_version == "v2.0"
    assert res.status == "production"


@pytest.mark.asyncio
async def test_model_management_get_lineage() -> None:
    mock_repo = AsyncMock(spec=ModelRepository)
    service = ModelManagementService(mock_repo)

    model_id = uuid.uuid4()
    mock_repo.get_model_lineage.return_value = {
        "model_id": str(model_id),
        "name": "classifier_sgd",
        "version": "v2.1",
        "kind": "classifier",
        "status": "production",
        "artifact_uri": "s3://models/clf_v2.1.joblib",
        "dataset_version_id": "ds-123",
        "dataset_name": "gold_dataset",
        "dataset_version": "2026.2",
        "dataset_record_count": 5000,
        "hyperparameters": {"alpha": 0.001, "loss": "log_loss"},
        "metrics": {"f1_macro": 0.895},
        "trained_at": "2026-09-20T10:00:00",
        "predictions_count": 142,
    }

    lineage = await service.get_model_lineage(model_id)
    assert lineage is not None
    assert lineage.model_id == str(model_id)
    assert lineage.dataset_name == "gold_dataset"
    assert lineage.predictions_count == 142
    assert lineage.metrics["f1_macro"] == 0.895


def test_ai_models_promote_and_rollback_endpoints() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.email = "admin@marketinsight.com"
    mock_user.is_active = True

    mock_service = AsyncMock(spec=ModelManagementService)
    model_id = uuid.uuid4()
    demoted_id = uuid.uuid4()

    mock_service.promote_model.return_value = PromotionResult(
        model_id=str(model_id),
        name="classifier_sgd",
        version="v2.0",
        previous_status="staging",
        new_status="production",
        demoted_model_id=str(demoted_id),
        demoted_version="v1.0",
    )

    mock_service.rollback_model.return_value = RollbackResult(
        demoted_model_id=str(model_id),
        demoted_version="v2.0",
        promoted_model_id=str(demoted_id),
        promoted_version="v1.0",
        status="production",
    )

    mock_service.get_model_lineage.return_value = ModelLineage(
        model_id=str(model_id),
        name="classifier_sgd",
        version="v2.0",
        kind="classifier",
        status="production",
        artifact_uri="s3://models/clf_v2.0.joblib",
        dataset_version_id="ds-1",
        dataset_name="gold-dataset",
        dataset_version="2026.2",
        dataset_record_count=1000,
        hyperparameters={"random_state": 42},
        metrics={"f1_macro": 0.88},
        trained_at="2026-09-20T12:00:00",
        predictions_count=50,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_model_management_service] = lambda: mock_service

    client = TestClient(app)

    # 1. Promote
    resp = client.post(f"/api/v1/ai/models/{model_id}/promote", json={"target_status": "production"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == str(model_id)
    assert data["new_status"] == "production"
    assert data["demoted_model_id"] == str(demoted_id)

    # 2. Rollback
    resp_rb = client.post("/api/v1/ai/models/rollback?kind=classifier")
    assert resp_rb.status_code == 200
    data_rb = resp_rb.json()
    assert data_rb["promoted_model_id"] == str(demoted_id)
    assert data_rb["status"] == "production"

    # 3. Lineage
    resp_lin = client.get(f"/api/v1/ai/models/{model_id}/lineage")
    assert resp_lin.status_code == 200
    data_lin = resp_lin.json()
    assert data_lin["model_id"] == str(model_id)
    assert data_lin["predictions_count"] == 50

    # 4. Retrain
    resp_retrain = client.post("/api/v1/ai/models/retrain", json={"random_state": 42})
    assert resp_retrain.status_code == 202
    data_retrain = resp_retrain.json()
    assert data_retrain["status"] == "staging"
    assert data_retrain["test_f1_macro"] > 0.8

    app.dependency_overrides.clear()
