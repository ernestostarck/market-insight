"""Unit tests for AI and NLP REST API endpoints (Fase 6.21).

Tests all 11 endpoints under /api/v1/ai:
1.  POST /ai/classify
2.  GET  /ai/classifications
3.  POST /ai/search
4.  GET  /ai/similar/{licitacion_id}
5.  POST /ai/entities
6.  POST /ai/products
7.  GET  /ai/categories
8.  POST /ai/relevance
9.  GET  /ai/reviews, POST /accept, POST /modify, GET /stats
10. GET  /ai/models
11. POST /ai/jobs, POST /ai/jobs/batch, GET /ai/jobs/{job_id}
"""

from __future__ import annotations

import datetime
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.dependencies import (
    get_classification_repository,
    get_classification_service,
    get_current_user,
    get_db,
    get_entity_extraction_service,
    get_model_repository,
    get_nlp_job_repository,
    get_nlp_service,
    get_product_extraction_service,
    get_relevance_service,
    get_review_service,
    get_semantic_search_service,
    get_taxonomy_service,
)
from app.main import app
from app.models.user import User
from app.nlp.confidence import ReviewReason
from app.nlp.entities import ExtractedEntity
from app.nlp.market_relevance import RelevanceResult
from app.nlp.product_attributes import ProductAttributes
from app.nlp.product_concepts import ProductConceptMatch
from app.repositories.vector_search import SimilarLicitacion


@pytest.fixture
def mock_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "analyst@marketinsight.com"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_user: User) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. POST /ai/classify
# ---------------------------------------------------------------------------
def test_ai_classify_endpoint(client: TestClient) -> None:
    mock_service = AsyncMock()
    mock_service.classify_text.return_value = {
        "category_code": "SALUD",
        "subcategory_code": "MEDICAMENTOS",
        "confidence_score": 0.92,
        "winning_method": "supervised",
        "rule_score": 0.85,
        "similarity_score": 0.88,
        "model_score": 0.95,
        "relevance_score": 0.90,
        "relevance_tier": "alta",
        "explanation": {"reason": "Clasificado por modelo supervisado."},
    }
    mock_preprocessor = MagicMock()
    mock_preprocessor.build_tender_document.return_value = SimpleNamespace(
        normalized_text="compra de medicamentos para hospital"
    )
    mock_service._preprocessor = mock_preprocessor

    app.dependency_overrides[get_classification_service] = lambda: mock_service

    payload = {
        "title": "Compra de medicamentos",
        "description": "Hospital Central",
        "items": ["Paracetamol 500mg"],
        "still_open": True,
    }
    response = client.post("/api/v1/ai/classify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category_code"] == "SALUD"
    assert data["confidence_score"] == 0.92
    assert data["relevance_tier"] == "alta"


# ---------------------------------------------------------------------------
# 2. GET /ai/classifications
# ---------------------------------------------------------------------------
def test_ai_classifications_endpoint(client: TestClient) -> None:
    mock_repo = AsyncMock()
    sample_cls = SimpleNamespace(
        id=uuid.uuid4(),
        licitacion_id=42,
        category_id=1,
        subcategory_id=2,
        taxonomy_version="taxonomy-2026.2",
        rule_score=0.8,
        similarity_score=0.75,
        model_score=0.9,
        confidence_score=0.88,
        relevance_score=0.85,
        relevance_tier="alta",
        explanation={"reason": "Predicción probada"},
        created_at=datetime.datetime(2026, 9, 20, 12, 0, 0),
    )
    mock_repo.list_by_licitacion_id.return_value = [sample_cls]
    app.dependency_overrides[get_classification_repository] = lambda: mock_repo

    response = client.get("/api/v1/ai/classifications?licitacion_id=42")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["licitacion_id"] == 42
    assert data["items"][0]["confidence_score"] == 0.88


# ---------------------------------------------------------------------------
# 3. POST /ai/search
# ---------------------------------------------------------------------------
def test_ai_semantic_search_endpoint(client: TestClient) -> None:
    mock_service = AsyncMock()
    mock_service.search.return_value = [
        SimilarLicitacion(
            licitacion_id=101,
            similarity=0.8912,
            category_id=3,
            subcategory_id=4,
            nombre="Adquisición de insumos médicos",
        )
    ]
    app.dependency_overrides[get_semantic_search_service] = lambda: mock_service

    payload = {"query": "insumos médicos de urgencia", "top_k": 5, "min_similarity": 0.5}
    response = client.post("/api/v1/ai/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "insumos médicos de urgencia"
    assert data["total"] == 1
    assert data["items"][0]["licitacion_id"] == 101
    assert data["items"][0]["similarity"] == 0.8912


# ---------------------------------------------------------------------------
# 4. GET /ai/similar/{licitacion_id}
# ---------------------------------------------------------------------------
def test_ai_similar_tenders_endpoint(client: TestClient) -> None:
    mock_service = AsyncMock()
    mock_service.find_similar_to_licitacion.return_value = [
        SimilarLicitacion(
            licitacion_id=202,
            similarity=0.9123,
            category_id=5,
            subcategory_id=6,
            nombre="Servicio de mantenimiento hospitalario",
        )
    ]
    app.dependency_overrides[get_semantic_search_service] = lambda: mock_service

    response = client.get("/api/v1/ai/similar/100?top_k=5")
    assert response.status_code == 200
    data = response.json()
    assert data["source_licitacion_id"] == 100
    assert data["total"] == 1
    assert data["items"][0]["licitacion_id"] == 202


# ---------------------------------------------------------------------------
# 5. POST /ai/entities
# ---------------------------------------------------------------------------
def test_ai_entities_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_service.extract_entities.return_value = [
        ExtractedEntity(
            entity_type="CANTIDAD",
            value="500 unidades",
            normalized_value="500",
            confidence_score=0.95,
            start_offset=0,
            end_offset=12,
        )
    ]
    app.dependency_overrides[get_entity_extraction_service] = lambda: mock_service

    payload = {
        "text": "500 unidades de guantes de látex quirúrgico",
        "organismo": "Hospital Regional",
    }
    response = client.post("/api/v1/ai/entities", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["entities"][0]["entity_type"] == "CANTIDAD"
    assert data["entities"][0]["normalized_value"] == "500"


# ---------------------------------------------------------------------------
# 6. POST /ai/products
# ---------------------------------------------------------------------------
def test_ai_products_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_service.extract_product_concepts.return_value = [
        ProductConceptMatch(
            concept_code="PARACETAMOL",
            category_code="SALUD",
            subcategory_code="FARMACOS",
            matched_term="paracetamol",
            start_offset=0,
            end_offset=11,
        )
    ]
    mock_service.extract_product_attributes.return_value = ProductAttributes(
        materiales=("almidón",),
        dimensiones=None,
        capacidad="500 mg",
        caracteristicas_tecnicas=("comprimidos",),
    )
    app.dependency_overrides[get_product_extraction_service] = lambda: mock_service

    payload = {
        "item_nombre": "Paracetamol 500mg comprimidos",
        "item_descripcion": "Caja de 20 tabletas",
    }
    response = client.post("/api/v1/ai/products", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["concepts"]) == 1
    assert data["concepts"][0]["concept_code"] == "PARACETAMOL"
    assert data["attributes"]["capacidad"] == "500 mg"
    assert "comprimidos" in data["attributes"]["caracteristicas_tecnicas"]


# ---------------------------------------------------------------------------
# 7. GET /ai/categories
# ---------------------------------------------------------------------------
def test_ai_categories_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_service.get_hierarchy.return_value = {
        "version": "taxonomy-2026.2",
        "categories": [
            {
                "code": "SALUD",
                "name": "Salud y Farmacéutica",
                "description": "Sector salud",
                "subcategories": [
                    {
                        "code": "MEDICAMENTOS",
                        "name": "Medicamentos",
                        "description": "Fármacos generales",
                        "concepts": [
                            {
                                "code": "ANALGESICOS",
                                "name": "Analgésicos",
                                "description": "Alivio del dolor",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    app.dependency_overrides[get_taxonomy_service] = lambda: mock_service

    response = client.get("/api/v1/ai/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "taxonomy-2026.2"
    assert len(data["categories"]) == 1
    assert data["categories"][0]["code"] == "SALUD"
    assert data["categories"][0]["subcategories"][0]["code"] == "MEDICAMENTOS"


# ---------------------------------------------------------------------------
# 8. POST /ai/relevance
# ---------------------------------------------------------------------------
def test_ai_relevance_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_service.compute.return_value = RelevanceResult(
        relevance_score=0.88,
        relevance_tier="alta",
        thematic_score=0.90,
        commercial_score=0.85,
        explanation={"summary": "Oportunidad comercial alta y temática afín."},
    )
    app.dependency_overrides[get_relevance_service] = lambda: mock_service

    payload = {
        "rule_score": 0.8,
        "similarity_score": 0.9,
        "model_score": 0.85,
        "still_open": True,
    }
    response = client.post("/api/v1/ai/relevance", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["relevance_score"] == 0.88
    assert data["relevance_tier"] == "alta"
    assert data["commercial_score"] == 0.85


# ---------------------------------------------------------------------------
# 9. Reviews: GET, POST /accept, POST /modify, GET /stats
# ---------------------------------------------------------------------------
def test_ai_reviews_queue_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_db = AsyncMock()

    queue_item = SimpleNamespace(
        classification_id=uuid.uuid4(),
        licitacion_id=77,
        title="Licitación dudosa",
        confidence_score=0.55,
        confidence_level=SimpleNamespace(value="low"),
        relevance_score=0.45,
        relevance_tier="media",
        category_code="SALUD",
        subcategory_code="EQUIPOS",
        needs_review=True,
        review_reasons=[ReviewReason.LOW_CONFIDENCE],
        priority_score=0.85,
    )
    mock_db.run_sync.return_value = [queue_item]

    app.dependency_overrides[get_review_service] = lambda: mock_service
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/ai/reviews?threshold=0.65")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["licitacion_id"] == 77
    assert data["items"][0]["confidence_level"] == "low"
    assert data["items"][0]["review_reasons"] == ["low_confidence"]


def test_ai_reviews_accept_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_db = AsyncMock()
    generated_review_id = uuid.uuid4()
    mock_db.run_sync.return_value = generated_review_id

    app.dependency_overrides[get_review_service] = lambda: mock_service
    app.dependency_overrides[get_db] = lambda: mock_db

    cls_id = uuid.uuid4()
    payload = {"reason": "Revisión confirmada por analista"}
    response = client.post(f"/api/v1/ai/reviews/{cls_id}/accept", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == str(generated_review_id)
    assert data["status"] == "accepted"


def test_ai_reviews_modify_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_db = AsyncMock()
    generated_review_id = uuid.uuid4()
    mock_db.run_sync.return_value = generated_review_id

    app.dependency_overrides[get_review_service] = lambda: mock_service
    app.dependency_overrides[get_db] = lambda: mock_db

    cls_id = uuid.uuid4()
    payload = {
        "category_code": "TECNOLOGIA",
        "subcategory_code": "SOFTWARE",
        "relevant": True,
        "relevance_tier": "alta",
        "reason": "Corrección de categoría a TI",
    }
    response = client.post(f"/api/v1/ai/reviews/{cls_id}/modify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == str(generated_review_id)
    assert data["status"] == "modified"


def test_ai_reviews_stats_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_db = AsyncMock()
    mock_db.run_sync.return_value = {
        "total_reviews": 150,
        "accepted": 130,
        "modified": 20,
        "agreement_rate": 0.8667,
    }

    app.dependency_overrides[get_review_service] = lambda: mock_service
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/ai/reviews/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total_reviews"] == 150
    assert data["stats"]["agreement_rate"] == 0.8667


# ---------------------------------------------------------------------------
# 10. GET /ai/models
# ---------------------------------------------------------------------------
def test_ai_models_endpoint(client: TestClient) -> None:
    mock_repo = AsyncMock()
    mock_repo.list_models.return_value = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name="classifier_sgd_logloss",
            version="v2.1",
            artifact_uri="s3://models/classifier_v2.1.joblib",
            state="production",
            metrics={"f1_macro": 0.89},
            created_at=datetime.datetime(2026, 9, 20, 10, 0, 0),
        )
    ]
    mock_repo.list_dataset_versions.return_value = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name="gold_dataset_chilecompra",
            version="2026.2",
            manifest={"num_samples": 5000},
            created_at=datetime.datetime(2026, 9, 20, 9, 0, 0),
        )
    ]
    app.dependency_overrides[get_model_repository] = lambda: mock_repo

    response = client.get("/api/v1/ai/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 1
    assert data["models"][0]["name"] == "classifier_sgd_logloss"
    assert data["models"][0]["state"] == "production"
    assert len(data["datasets"]) == 1
    assert data["datasets"][0]["version"] == "2026.2"


# ---------------------------------------------------------------------------
# 11. Jobs: POST /jobs, POST /jobs/batch, GET /jobs/{job_id}
# ---------------------------------------------------------------------------
def test_ai_create_job_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    mock_service.submit.return_value = "celery-task-999"
    app.dependency_overrides[get_nlp_service] = lambda: mock_service

    payload = {
        "licitacion_id": 888,
        "text_hash": "f" * 64,
        "taxonomy_version": "taxonomy-2026.2",
        "dictionary_version": "dictionary-2026.1",
    }
    response = client.post("/api/v1/ai/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["task_id"] == "celery-task-999"
    assert "888:" in data["idempotency_key"]


def test_ai_create_batch_jobs_endpoint(client: TestClient) -> None:
    mock_service = MagicMock()
    app.dependency_overrides[get_nlp_service] = lambda: mock_service

    payload = {
        "jobs": [
            {
                "licitacion_id": 1,
                "text_hash": "1" * 64,
                "taxonomy_version": "taxonomy-2026.2",
                "dictionary_version": "dictionary-2026.1",
            },
            {
                "licitacion_id": 2,
                "text_hash": "2" * 64,
                "taxonomy_version": "taxonomy-2026.2",
                "dictionary_version": "dictionary-2026.1",
            },
        ]
    }

    with patch("app.worker.nlp_tasks.process_nlp_batch.apply_async") as mock_async:
        mock_task = MagicMock()
        mock_task.id = "batch-task-uuid"
        mock_async.return_value = mock_task

        response = client.post("/api/v1/ai/jobs/batch", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "batch-task-uuid"
        assert data["total_jobs"] == 2


def test_ai_get_job_status_from_redis(client: TestClient) -> None:
    with patch("app.api.v1.endpoints.ai._job_tracker") as mock_tracker:
        mock_tracker.get_job_state.return_value = {
            "task_id": "task-xyz",
            "idempotency_key": "idemp-xyz",
            "licitacion_id": 55,
            "status": "succeeded",
            "duration_seconds": 1.25,
            "result": {"status": "succeeded"},
        }

        response = client.get("/api/v1/ai/jobs/task-xyz")
        assert response.status_code == 200
        data = response.json()
        assert data["celery_task_id"] == "task-xyz"
        assert data["status"] == "succeeded"
        assert data["duration_seconds"] == 1.25


def test_ai_get_job_status_from_db(client: TestClient) -> None:
    job_uuid = uuid.uuid4()
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = SimpleNamespace(
        id=job_uuid,
        celery_task_id="celery-abc",
        idempotency_key="idemp-abc",
        licitacion_id=66,
        status="succeeded",
        duration_seconds=0.95,
        completed_stages=["classification", "embeddings"],
        pending_stages=[],
        error=None,
        result_summary={"ok": True},
        retries=0,
    )
    app.dependency_overrides[get_nlp_job_repository] = lambda: mock_repo

    with patch("app.api.v1.endpoints.ai._job_tracker") as mock_tracker:
        mock_tracker.get_job_state.return_value = None

        response = client.get(f"/api/v1/ai/jobs/{job_uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job_uuid)
        assert data["status"] == "succeeded"
        assert data["duration_seconds"] == 0.95
        assert data["completed_stages"] == ["classification", "embeddings"]


def test_ai_get_job_status_not_found(client: TestClient) -> None:
    mock_repo = AsyncMock()
    mock_repo.get_by_celery_task_id.return_value = None
    app.dependency_overrides[get_nlp_job_repository] = lambda: mock_repo

    with patch("app.api.v1.endpoints.ai._job_tracker") as mock_tracker:
        mock_tracker.get_job_state.return_value = None

        response = client.get("/api/v1/ai/jobs/nonexistent-id")
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]


def test_ai_create_feedback_endpoint(client: TestClient) -> None:
    msg_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_feedback = SimpleNamespace(
        id=uuid.uuid4(),
        message_id=msg_id,
        conversation_id=conv_id,
        user_id=uuid.uuid4(),
        rating=1,
        reason=None,
        comment="Respuesta útil",
        sources_used=[],
        retrieval_strategy="sql",
        model="gemini-2.5-flash",
        created_at=datetime.datetime.now(datetime.UTC),
    )
    mock_db.run_sync = AsyncMock(return_value=mock_feedback)
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "message_id": str(msg_id),
        "rating": 1,
        "comment": "Respuesta útil",
    }
    response = client.post("/api/v1/ai/feedback", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["message_id"] == str(msg_id)
    assert data["rating"] == 1


def test_ai_feedback_stats_endpoint(client: TestClient) -> None:
    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(
        return_value={
            "total_feedback": 15,
            "positive_count": 12,
            "negative_count": 3,
            "positive_ratio": 0.8,
            "reasons_breakdown": {"hallucination": 2, "outdated_info": 1},
        }
    )
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/ai/feedback/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_feedback"] == 15
    assert data["positive_ratio"] == 0.8


def test_ai_cost_summary_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/ai/cost/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_cost_usd" in data
    assert "total_tokens" in data


def test_ai_evaluate_benchmark_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/ai/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert "total_cases" in data
    assert "pass_rate" in data
    assert data["total_cases"] >= 12

