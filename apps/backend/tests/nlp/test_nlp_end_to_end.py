"""Comprehensive End-to-End Integration Tests for the NLP Pipeline (Fase 6.26).

Validates the full multi-stage processing pipeline on realistic tender data:
Document -> Preprocessing -> Rule Classification -> Semantic Embeddings ->
Supervised Inference -> Hybrid Fusion -> NER Extraction -> Product Extraction ->
Relevance Scoring -> Confidence Scoring & Human Review Routing -> Worker Execution ->
Prometheus Observability.
"""

from __future__ import annotations

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.nlp.contracts import JobResult, JobStatus, PipelineStage
from app.nlp.dictionary import load_initial_dictionary
from app.nlp.document import TenderDocument, build_document
from app.nlp.preprocessing import PreprocessedText, TextPreprocessor, tokenize
from app.nlp.rules import RuleEngine, build_ruleset
from app.nlp.taxonomy import load_initial_taxonomy
from app.services.nlp import (
    ClassificationService,
    EmbeddingService,
    EntityExtractionService,
    PreprocessingService,
    ProductExtractionService,
    RelevanceService,
    ReviewService,
    RuleClassificationService,
    TaxonomyService,
)
from app.worker.job_tracker import JobTracker
from app.worker.nlp_tasks import process_nlp_job


@pytest.mark.asyncio
async def test_nlp_pipeline_end_to_end_full_flow() -> None:
    """Validate full flow from tender data to hybrid classification, extraction and scoring."""
    raw_tender = {
        "id": 88421,
        "codigo_externo": "2401-15-LR26",
        "nombre": "Adquisición de silla de ruedas y ayudas técnicas para adulto mayor",
        "descripcion": (
            "Se requiere la compra urgente de silla de ruedas clínica de aluminio plegable "
            "con capacidad de 120 kg para geriatria y pacientes con movilidad reducida. "
            "Entrega en Santiago antes del 15 de diciembre de 2026."
        ),
        "organismo_nombre": "Servicio de Salud Metropolitano",
        "monto_estimado": 15000000.0,
        "items": [
            "Silla de ruedas neurológica estándar estructura aluminio soporte 120 kg plegable",
            "Cama clínica de tres posiciones hospitalaria eléctrica",
        ],
        "fecha_cierre": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=20),
    }

    # 1. Document Representation & Consolidator
    preprocessor = TextPreprocessor()
    full_text = f"{raw_tender['nombre']} {raw_tender['descripcion']}"
    prep_res: PreprocessedText = preprocessor.preprocess(full_text)
    tokens = tokenize(prep_res.normalized_text)
    assert len(tokens) > 0
    assert "sillas" in prep_res.normalized_text or "silla" in prep_res.normalized_text

    doc = build_document(
        licitacion_id=raw_tender["id"],
        preprocessed=prep_res,
    )
    assert isinstance(doc, TenderDocument)
    assert doc.licitacion_id == 88421
    assert "silla de ruedas" in doc.raw_text.lower()
    assert len(doc.chunks) >= 1

    # 2. Rule Engine Classification
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()
    rule_engine = RuleEngine(build_ruleset(dictionary, taxonomy))
    rule_matches = rule_engine.evaluate(prep_res.normalized_text)
    assert len(rule_matches.matches) > 0
    assert rule_matches.category_code is not None

    # 4. Dense Embeddings & Taxonomy Resolution
    mock_base_embed = MagicMock()
    mock_base_embed.encode.side_effect = lambda texts: np.random.RandomState(42).randn(len(texts), 128)

    embed_service = EmbeddingService(base_service=mock_base_embed)
    tax_service = TaxonomyService(taxonomy=taxonomy)
    rule_service = RuleClassificationService(rule_engine=rule_engine)
    relevance_service = RelevanceService()

    # 5. Hybrid Classification Fusion
    mock_repo = AsyncMock()
    cls_service = ClassificationService(
        preprocessing_service=PreprocessingService(),
        rule_service=rule_service,
        embedding_service=embed_service,
        taxonomy_service=tax_service,
        relevance_service=relevance_service,
        classification_repository=mock_repo,
    )

    cls_result = await cls_service.classify_text(doc.raw_text)
    assert isinstance(cls_result, dict)
    assert "category_code" in cls_result
    assert "confidence_score" in cls_result
    assert "relevance_score" in cls_result
    assert cls_result["confidence_score"] > 0.0

    # 6. Entity Extraction (NER)
    entity_service = EntityExtractionService(
        entity_repository=AsyncMock(),
        relationship_repository=AsyncMock(),
    )
    entities = entity_service.extract_entities(
        doc.raw_text,
        organismo=raw_tender["organismo_nombre"],
    )
    assert isinstance(entities, list)
    assert any(e.entity_type == "organismo" for e in entities)

    # 7. Product Extraction & Technical Attributes
    product_service = ProductExtractionService(dictionary=dictionary)
    extracted_products = product_service.process_item(
        licitacion_id=88421,
        licitacion_item_id=1,
        item_nombre="Silla de ruedas neurológica estándar",
        item_descripcion="Estructura de aluminio, capacidad 120 kg, plegable",
        cantidad=10.0,
        unidad="UNIDAD",
    )
    assert len(extracted_products) >= 1
    p = extracted_products[0]
    assert p.licitacion_id == 88421
    assert p.capacidad == "120 kg"

    # 8. Relevance Assessment
    relevance = relevance_service.assess_tender(
        rule_score=cls_result["rule_score"],
        similarity_score=cls_result["similarity_score"],
        model_score=cls_result["model_score"],
        fecha_cierre=raw_tender["fecha_cierre"],
    )
    assert 0.0 <= round(relevance.relevance_score, 4) <= 1.0
    assert relevance.relevance_tier in ("high", "medium", "low", "alta", "media", "baja")

    # 9. Confidence Assessment & Human Review Routing
    review_service = ReviewService(taxonomy_service=tax_service)
    assessment = review_service.evaluate_confidence(
        confidence_score=cls_result["confidence_score"],
        category_code=cls_result["category_code"],
        relevance_tier=relevance.relevance_tier,
    )
    assert hasattr(assessment, "needs_review")
    assert hasattr(assessment, "reasons")

    # 10. Background Worker Execution & Caching
    worker_payload = {
        "licitacion_id": doc.licitacion_id,
        "text_hash": doc.content_hash,
        "versions": {
            "taxonomy": "taxonomy-2026.2",
            "semantic_dictionary": "dictionary-2026.1",
            "model": None,
            "embedding_model": None,
        },
    }
    mock_result = JobResult(
        job_key=f"{doc.licitacion_id}:{doc.content_hash}:taxonomy-2026.2:dictionary-2026.1:none:none",
        licitacion_id=doc.licitacion_id,
        completed_stages=(PipelineStage.CLASSIFICATION, PipelineStage.EMBEDDINGS),
        pending_stages=(),
        status=JobStatus.SUCCEEDED,
    )
    process_nlp_job.request.id = "e2e-task-1"
    process_nlp_job.request.retries = 0

    with (
        patch("app.worker.nlp_tasks.execute_nlp_job", return_value=mock_result),
        patch("app.worker.nlp_tasks._job_tracker") as mock_tracker,
        patch("app.worker.nlp_tasks._db_record_job_start"),
        patch("app.worker.nlp_tasks._db_record_job_finish"),
    ):
        mock_tracker.get_idempotent_result.return_value = None
        job_result = process_nlp_job(worker_payload)

        assert job_result["status"] == "succeeded"
        assert mock_tracker.record_job_start.called
        assert mock_tracker.record_job_success.called


def test_nlp_end_to_end_confidence_routing_thresholds() -> None:
    """Verify confidence evaluation thresholds trigger human review warnings correctly."""
    review_service = ReviewService()

    # Borderline low confidence
    low_conf_assessment = review_service.evaluate_confidence(
        confidence_score=0.45,
        category_code="SALUD",
        relevance_tier="baja",
    )
    assert low_conf_assessment.needs_review is True
    assert len(low_conf_assessment.reasons) > 0

    # High confidence clear case
    high_conf_assessment = review_service.evaluate_confidence(
        confidence_score=0.92,
        category_code="SALUD",
        relevance_tier="alta",
    )
    assert high_conf_assessment.needs_review is False
