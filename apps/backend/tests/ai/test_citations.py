"""Unit tests for CitationManager and citation routing (Fase 9.14)."""

from app.ai.citations import CitationManager
from app.ai.contracts import Source


def test_extract_explicit_citations():
    manager = CitationManager()

    context_sources = [
        Source(
            id="1234-56-LP24",
            source_type="tender",
            title="Licitación Ambulancias",
            snippet="Adquisición de ambulancias 4x4",
            score=0.92,
        ),
        Source(
            id="456-78-CM24",
            source_type="purchase_order",
            title="Orden de Compra Insumos",
            snippet="Guantes quirúrgicos",
            score=0.85,
        ),
    ]

    answer_text = (
        "El Servicio de Salud adjudicó ambulancias por $45.000.000 CLP [Fuente: licitacion 1234-56-LP24]. "
        "Adicionalmente, se emitieron insumos críticos [Fuente: orden_compra 456-78-CM24]."
    )

    citations = manager.extract_citations(answer_text, context_sources)

    assert len(citations) == 2
    assert citations[0].source_id == "1234-56-LP24"
    assert citations[0].source_type == "tender"
    assert citations[0].is_verified is True
    assert citations[0].target_route == "/licitaciones/1234-56-LP24"
    assert citations[0].relevance == 0.92

    assert citations[1].source_id == "456-78-CM24"
    assert citations[1].source_type == "purchase_order"
    assert citations[1].is_verified is True
    assert citations[1].target_route == "/ordenes-compra/456-78-CM24"


def test_detect_fictitious_citations():
    manager = CitationManager()

    context_sources = [
        Source(id="LIC-REAL-01", source_type="tender", title="Licitación Real")
    ]

    # Model hallucinations: references a fictitious tender "LIC-FAKE-99"
    answer_text = "Se adjudicó una licitación de prueba [Fuente: licitacion LIC-FAKE-99]."

    citations = manager.extract_citations(answer_text, context_sources)

    assert len(citations) == 1
    assert citations[0].source_id == "LIC-FAKE-99"
    assert citations[0].is_verified is False

    fictitious = manager.get_fictitious_citations(citations)
    assert len(fictitious) == 1
    assert fictitious[0].source_id == "LIC-FAKE-99"


def test_extract_numbered_citations():
    manager = CitationManager()

    context_sources = [
        Source(id="DOC-01", source_type="tender", title="Primer Documento"),
        Source(id="DOC-02", source_type="tender", title="Segundo Documento"),
    ]

    answer_text = "Primer hallazgo analítico [Fuente #1] y segundo hallazgo [Fuente #2]."
    citations = manager.extract_citations(answer_text, context_sources)

    assert len(citations) == 2
    assert citations[0].source_id == "DOC-01"
    assert citations[0].is_verified is True
    assert citations[1].source_id == "DOC-02"
    assert citations[1].is_verified is True


def test_fallback_citations_when_no_tags_present():
    manager = CitationManager()

    context_sources = [
        Source(id="MART-01", source_type="mart", title="Resumen de Compras"),
    ]

    answer_text = "Respuesta sin etiquetas de cita explícitas."
    citations = manager.extract_citations(answer_text, context_sources)

    assert len(citations) == 1
    assert citations[0].source_id == "MART-01"
    assert citations[0].is_verified is True
    assert citations[0].target_route == "/analytics"
