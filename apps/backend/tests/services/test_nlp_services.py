"""Unit tests for the 11 NLP domain services (Fase 6.18)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.models.knowledge import Classification, Document, Entity
from app.nlp.confidence import ConfidenceLevel
from app.nlp.dictionary import DomainTheme
from app.repositories.vector_search import SimilarLicitacion
from app.services.nlp import (
    ClassificationService,
    DictionaryService,
    EmbeddingService,
    EntityExtractionService,
    PreprocessingService,
    ProductExtractionService,
    RelevanceService,
    ReviewService,
    RuleClassificationService,
    SemanticSearchService,
    TaxonomyService,
)


def test_preprocessing_service() -> None:
    service = PreprocessingService()
    text = "Silla de ruedas para HOSPITAL en Valparaíso."
    result = service.preprocess(text)
    assert result.original_text == text
    assert "silla de ruedas" in result.normalized_text

    doc = service.build_tender_document(
        title="Adquisición de sillas",
        description="Para geriatría",
        item_texts=["Silla estándar"],
    )
    assert "silla" in doc.normalized_text

    consolidated = service.build_consolidated_document(
        licitacion_id=101,
        title="Adquisición de sillas",
        description="Para geriatría",
        item_texts=["Silla estándar"],
    )
    assert consolidated.licitacion_id == 101
    assert len(consolidated.chunks) >= 1
    assert consolidated.content_hash


@pytest.mark.asyncio
async def test_preprocessing_service_persistence() -> None:
    doc_repo = AsyncMock()
    doc_repo.get_by_content_hash.return_value = None
    doc_repo.create.side_effect = lambda d: d

    chunk_repo = AsyncMock()
    chunk_repo.create_many.return_value = []

    service = PreprocessingService(
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
    )

    saved = await service.process_and_store_tender(
        licitacion_id=42,
        title="Compra de andadores",
        description="Andadores para personas mayores",
        item_texts=["Andador plegable"],
    )
    assert saved.licitacion_id == 42
    assert doc_repo.create.called
    assert chunk_repo.create_many.called


def test_dictionary_service() -> None:
    service = DictionaryService()
    assert "2026" in service.get_version()

    entry = service.get_entry("silla de ruedas")
    assert entry is not None
    assert entry.concept

    # List terms filtered by theme
    geriatria_entries = service.list_terms(DomainTheme.GERIATRIA)
    assert len(geriatria_entries) > 0
    assert all(e.theme == DomainTheme.GERIATRIA for e in geriatria_entries)

    # Surface form match search
    matches = service.find_matches("Se solicita silla de ruedas plegable y andador.")
    assert len(matches) >= 1
    found_surface_forms = [m.surface_form.lower() for m in matches]
    assert any("silla de ruedas" in form for form in found_surface_forms)


def test_taxonomy_service() -> None:
    service = TaxonomyService()
    assert service.get_version().startswith("taxonomy-")

    # Categories
    cat = service.resolve_category("health")
    assert cat is not None
    assert cat.name

    # Subcategories
    sub = service.resolve_subcategory("health", "medical-equipment")
    assert sub is not None

    # Locate concept
    located = service.locate_concept("geriatria")
    assert located is not None
    c_cat, c_sub, c_con = located
    assert c_con.code == "geriatria"

    # Hierarchy and validation
    hierarchy = service.get_hierarchy()
    assert "categories" in hierarchy
    assert len(hierarchy["categories"]) > 0

    errors = service.validate()
    assert errors == []


def test_rule_classification_service() -> None:
    service = RuleClassificationService()
    eval_res = service.evaluate("Se requiere adquisicion de silla de ruedas para hospital.")
    assert eval_res.category_code is not None
    assert eval_res.score > 0
    assert len(eval_res.matches) > 0

    eval_tender = service.evaluate_tender(
        title="Compra de audifono",
        description="Para adultos mayores con hipoacusia",
        items=["Audifono digital"],
    )
    assert eval_tender.category_code is not None


def test_embedding_service() -> None:
    mock_base = MagicMock()
    mock_base.encode.return_value = np.array([[0.5, 0.5, 0.0]], dtype=np.float32)

    service = EmbeddingService(base_service=mock_base)
    res = service.encode(["prueba de texto"])
    assert res.shape == (1, 3)

    vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sim = service.compute_similarity(vec_a, vec_b)
    assert pytest.approx(sim, 0.001) == 1.0


@pytest.mark.asyncio
async def test_semantic_search_service() -> None:
    mock_repo = AsyncMock()
    mock_repo.search_by_vector.return_value = [
        SimilarLicitacion(licitacion_id=1, similarity=0.92, category_id=1, subcategory_id=1, nombre="Sillas")
    ]
    mock_repo.find_similar_to_licitacion.return_value = [
        SimilarLicitacion(licitacion_id=2, similarity=0.88, category_id=1, subcategory_id=1, nombre="Andadores")
    ]
    mock_repo.search_by_concept.return_value = [
        SimilarLicitacion(licitacion_id=3, similarity=0.85, category_id=1, subcategory_id=1, nombre="Camas")
    ]
    mock_repo.search_by_category.return_value = [
        SimilarLicitacion(licitacion_id=4, similarity=0.81, category_id=1, subcategory_id=1, nombre="Insumos")
    ]

    mock_emb = MagicMock()
    mock_emb.encode.side_effect = lambda texts: np.zeros((len(list(texts)), 384), dtype=np.float32)

    service = SemanticSearchService(
        vector_repository=mock_repo,
        embedding_service=mock_emb,
    )

    results = await service.search("sillas de ruedas", top_k=5)
    assert len(results) == 1
    assert results[0].licitacion_id == 1

    sim_lic = await service.find_similar_to_licitacion(1)
    assert len(sim_lic) == 1

    concept_results = await service.search_by_concept("geriatria")
    assert len(concept_results) == 1

    cat_results = await service.search_by_category("health")
    assert len(cat_results) == 1


@pytest.mark.asyncio
async def test_classification_service() -> None:
    mock_preprocessor = PreprocessingService()
    mock_rules = RuleClassificationService()

    mock_emb = MagicMock()
    mock_emb._base = MagicMock()
    mock_emb._base.encode.side_effect = lambda texts: np.zeros((len(list(texts)), 384), dtype=np.float32)
    mock_emb.encode.side_effect = lambda texts: np.zeros((len(list(texts)), 384), dtype=np.float32)

    tax_service = TaxonomyService()
    rel_service = RelevanceService()

    service = ClassificationService(
        preprocessing_service=mock_preprocessor,
        rule_service=mock_rules,
        embedding_service=mock_emb,
        taxonomy_service=tax_service,
        relevance_service=rel_service,
    )

    result = await service.classify_text("Adquisición de silla de ruedas para rehabilitación.")
    assert "category_code" in result
    assert "confidence_score" in result
    assert "relevance_score" in result
    assert "explanation" in result

    # Persistence test
    mock_repo = AsyncMock()
    mock_repo.create.side_effect = lambda c: c
    service._repo = mock_repo

    saved = await service.classify_and_store_tender(
        licitacion_id=99,
        title="Silla de ruedas",
        description="Para centro de salud",
        items=["Silla plegable"],
    )
    assert saved.licitacion_id == 99
    assert mock_repo.create.called


def test_entity_extraction_service() -> None:
    service = EntityExtractionService()
    text = "Se solicitan 10 unidades el 15/10/2026 por $500.000 marca Ortopedia modelo Pro."
    entities = service.extract_entities(
        text,
        organismo="Hospital Regional",
        region="Valparaíso",
        comuna="Viña del Mar",
        items=["Silla neurológica"],
    )

    types = {e.entity_type for e in entities}
    assert "cantidad" in types
    assert "unidad" in types
    assert "fecha" in types
    assert "monto" in types
    assert "marca" in types
    assert "modelo" in types
    assert "organismo" in types
    assert "region" in types
    assert "comuna" in types
    assert "producto" in types


@pytest.mark.asyncio
async def test_entity_extraction_persistence() -> None:
    mock_repo = AsyncMock()
    mock_repo.create_many.side_effect = lambda items: items
    service = EntityExtractionService(entity_repository=mock_repo)

    text = "5 unidades de andador"
    saved = await service.extract_and_store(
        licitacion_id=77,
        text=text,
        organismo="CESFAM",
    )
    assert len(saved) >= 2
    assert mock_repo.create_many.called


def test_product_extraction_service() -> None:
    service = ProductExtractionService()
    text = "Silla de ruedas de aluminio plegable de 60 cm x 90 cm con capacidad de 120 kg."
    concepts = service.extract_product_concepts(text)
    assert len(concepts) >= 1

    attrs = service.extract_product_attributes(text)
    assert "aluminio" in attrs.materiales
    assert "plegable" in attrs.caracteristicas_tecnicas
    assert attrs.dimensiones is not None
    assert attrs.capacidad is not None

    products = service.process_item(
        licitacion_id=5,
        licitacion_item_id=12,
        item_nombre="Silla de ruedas",
        item_descripcion="Estructura de aluminio",
        cantidad=4.0,
        unidad="unidades",
    )
    assert len(products) >= 1
    p = products[0]
    assert p.licitacion_id == 5
    assert p.cantidad == 4.0
    assert p.unidad == "unidades"


def test_relevance_service() -> None:
    service = RelevanceService()
    res_open = service.compute(rule_score=3.0, similarity_score=0.8, model_score=0.9, still_open=True)
    assert res_open.relevance_score > 0.5
    assert res_open.relevance_tier in ("high", "medium", "low")

    res_closed = service.compute(rule_score=3.0, similarity_score=0.8, model_score=0.9, still_open=False)
    assert res_closed.relevance_score < res_open.relevance_score

    future_date = datetime(2099, 1, 1, tzinfo=timezone.utc)
    res_tender = service.assess_tender(
        rule_score=2.0,
        similarity_score=0.7,
        model_score=None,
        fecha_cierre=future_date,
    )
    assert res_tender.relevance_tier in ("high", "medium", "low")


def test_review_service() -> None:
    service = ReviewService()
    assessment = service.evaluate_confidence(0.9, category_code="health")
    assert assessment.level == ConfidenceLevel.HIGH
    assert not assessment.needs_review

    low_assessment = service.evaluate_confidence(0.3, category_code="health")
    assert low_assessment.level == ConfidenceLevel.LOW
    assert low_assessment.needs_review

    # Mock DB functions for queue, accept, modify, stats
    mock_conn = MagicMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.nlp.review.fetch_review_queue",
            lambda conn, **kw: [MagicMock()],
        )
        mp.setattr(
            "app.services.nlp.review.record_human_review",
            lambda conn, **kw: uuid.uuid4(),
        )
        mp.setattr(
            "app.services.nlp.review.incorporate_feedback_to_gold_dataset",
            lambda conn, **kw: {"incorporated_count": 5},
        )
        mp.setattr(
            "app.services.nlp.review.get_review_statistics",
            lambda conn: {"total_reviews": 10},
        )

        queue = service.get_queue(mock_conn)
        assert len(queue) == 1

        rev_id = service.accept(mock_conn, uuid.uuid4(), uuid.uuid4())
        assert isinstance(rev_id, uuid.UUID)

        mod_id = service.modify(
            mock_conn,
            uuid.uuid4(),
            uuid.uuid4(),
            category_code="health",
            subcategory_code="medical-equipment",
            relevant=True,
            relevance_tier="high",
            reason="Corregido por experto.",
        )
        assert isinstance(mod_id, uuid.UUID)

        sync_res = service.sync_gold_dataset(mock_conn, uuid.uuid4())
        assert sync_res["incorporated_count"] == 5

        stats = service.get_stats(mock_conn)
        assert stats["total_reviews"] == 10
