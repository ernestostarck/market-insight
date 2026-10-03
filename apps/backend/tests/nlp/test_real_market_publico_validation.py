"""Automated Test Suite for Phase 6.28: End-to-End Validation on Real Mercado Público Data.

Verifies that the complete NLP & Knowledge Layer pipeline achieves the required
performance benchmarks on real ChileCompra procurement documents.
"""

from __future__ import annotations

import datetime
import pytest

from app.nlp.confidence import ConfidenceLevel
from app.nlp.validation.dataset import get_validation_tenders
from app.nlp.validation.validator import RealMarketPublicoValidator, ValidationSummary


@pytest.fixture(scope="module")
def validation_summary() -> ValidationSummary:
    """Run validation once for all test assertions in this module."""
    validator = RealMarketPublicoValidator()
    return validator.run_validation()


def test_validation_dataset_integrity() -> None:
    """Validate schema, diversity, and attributes of the 20 real Mercado Público tenders."""
    tenders = get_validation_tenders()
    assert len(tenders) == 20

    categories = {t.expected_category for t in tenders}
    assert categories == {"health", "construction", "technology", "not_relevant"}

    for t in tenders:
        assert t.id > 0
        assert len(t.codigo_externo) >= 8
        assert len(t.nombre) > 10
        assert len(t.descripcion) > 20
        assert t.monto_estimado > 0
        assert "-" in t.rut_comprador
        assert len(t.items) >= 1
        for item in t.items:
            assert item.correlativo >= 1
            assert len(item.codigo_producto) >= 6
            assert len(item.nombre) > 0
            assert item.cantidad > 0
            assert item.precio_referencial > 0


def test_full_pipeline_validation_on_real_data(validation_summary: ValidationSummary) -> None:
    """Execute complete 18-step validator and assert benchmark metrics."""
    summary = validation_summary

    # 1. Macro-level predictive benchmarks
    assert summary.metrics.total_tenders == 20
    assert summary.metrics.f1_macro >= 0.85, f"F1 Macro {summary.metrics.f1_macro} below 0.85"
    assert summary.metrics.accuracy >= 0.85, f"Accuracy {summary.metrics.accuracy} below 0.85"
    assert summary.metrics.relevance_accuracy >= 0.90, f"Relevance Accuracy {summary.metrics.relevance_accuracy} below 0.90"

    # 2. Performance & latency constraints (< 50ms per document)
    assert summary.metrics.mean_latency_ms < 50.0
    assert summary.metrics.p95_latency_ms < 100.0

    # 3. Observability & Data Drift
    assert summary.metrics.drift_report.drift_detected is False
    assert summary.metrics.drift_report.kl_divergence < 0.25

    # 4. Human-in-the-loop triggers
    assert summary.metrics.human_reviews_triggered > 0

    # 5. Infrastructure contracts
    assert summary.async_simulation_verified is True
    assert summary.persistence_verified is True
    assert summary.human_review_simulation_verified is True

    # 6. Lineage and versioning
    assert summary.taxonomy_version.value == "taxonomy-2026.1"
    assert summary.dictionary_version.value == "dictionary-2026.1"
    assert summary.model_lineage.status == "production"
    assert summary.model_lineage.predictions_count == 20


def test_chilean_entities_and_ner_extraction(validation_summary: ValidationSummary) -> None:
    """Verify NER entity extraction across real tender texts."""
    summary = validation_summary

    # Tender 101 (Sillas de ruedas: 120 kg, 35 unidades)
    t101 = next(r for r in summary.results if r.tender_id == 101)
    assert t101.entities_count > 0
    entity_values = [e.value.lower() for e in t101.entities]
    assert any("120 kg" in v or "120" in v for v in entity_values)


def test_product_and_attribute_extraction_on_real_items(validation_summary: ValidationSummary) -> None:
    """Verify product concept and attribute extraction on item specifications."""
    summary = validation_summary

    # Tender 101 has silla de ruedas and andador
    t101 = next(r for r in summary.results if r.tender_id == 101)
    concept_codes = [c.concept_code for c in t101.product_concepts]
    assert "silla_de_ruedas" in concept_codes
    assert "andador" in concept_codes

    # Attributes should detect aluminio material
    materials = [m for attr in t101.product_attributes for m in (attr.materiales or [])]
    assert any("aluminio" in m.lower() for m in materials)

    # Tender 108 has baño accesible and barra de apoyo
    t108 = next(r for r in summary.results if r.tender_id == 108)
    concept_codes_108 = [c.concept_code for c in t108.product_concepts]
    assert "bano_accesible" in concept_codes_108 or "barra_de_apoyo" in concept_codes_108


def test_similar_tenders_semantic_coherence(validation_summary: ValidationSummary) -> None:
    """Verify vector search retrieves topically relevant nearest neighbors."""
    summary = validation_summary

    # Tender 101 (sillas de ruedas, health) top neighbors should include other health/rehab tenders
    t101 = next(r for r in summary.results if r.tender_id == 101)
    assert len(t101.similar_tenders) == 3
    top_neighbor_code = t101.similar_tenders[0][0]

    tenders = get_validation_tenders()
    neighbor = next(t for t in tenders if t.codigo_externo == top_neighbor_code)
    # Nearest neighbor to a healthcare mobility tender should be in health or construction accessibility
    assert neighbor.expected_category in ("health", "construction")


def test_confidence_and_human_review_audit_loop(validation_summary: ValidationSummary) -> None:
    """Verify uncertainty detection and simulated human review resolution."""
    summary = validation_summary

    # Tender 119 ("Servicio de mantención general" - sparse/ambiguous)
    t119 = next(r for r in summary.results if r.tender_id == 119)
    assert t119.confidence_assessment.needs_review is True
    assert t119.confidence_assessment.level in (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM)
