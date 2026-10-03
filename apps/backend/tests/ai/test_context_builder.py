"""Unit tests for SecureContextBuilder (Fase 9.10)."""

from app.ai.context_builder import SecureContextBuilder
from app.ai.contracts import RetrievalResult, RetrievalStrategy, Source


def test_context_builder_injection_demarcation():
    builder = SecureContextBuilder(token_budget=1000)

    retrieval_result = RetrievalResult(
        strategy_used=RetrievalStrategy.SEMANTIC,
        items=[
            {
                "licitacion_id": "1234-56-LP24",
                "titulo": "Adquisición de Servidores",
                "chunk_text": "Servidores rack 2U para data center central.",
                "score": 0.92,
            }
        ],
        sources=[
            Source(
                id="1234-56-LP24",
                source_type="tender",
                title="Adquisición de Servidores",
                snippet="Servidores rack 2U para data center central.",
                score=0.92,
            )
        ],
        total_results=1,
    )

    context = builder.build_context("servidores rack", retrieval_result)

    # Must contain injection protection markers
    assert "### CONTEXT - UNTRUSTED DATA BEGIN ###" in context.formatted_prompt_context
    assert "### CONTEXT - UNTRUSTED DATA END ###" in context.formatted_prompt_context
    assert "1234-56-LP24" in context.formatted_prompt_context
    assert "Servidores rack 2U" in context.formatted_prompt_context
    assert len(context.sources) == 1
    assert context.token_estimate > 0


def test_context_builder_formats_sql_tabular_data():
    builder = SecureContextBuilder(token_budget=1000)

    sql_items = [
        {"comprador_nombre": "Hospital Salvador", "monto_total_adjudicado": 45000000},
        {"comprador_nombre": "Municipalidad de Santiago", "monto_total_adjudicado": 32000000},
    ]

    retrieval_result = RetrievalResult(
        strategy_used=RetrievalStrategy.SQL,
        items=sql_items,
        sql_executed="SELECT comprador_nombre, SUM(monto) FROM licitaciones GROUP BY 1",
        sources=[
            Source(
                id="mart_purchases",
                source_type="mart",
                title="Gasto agregado por comprador",
            )
        ],
        total_results=2,
    )

    context = builder.build_context("gasto por comprador", retrieval_result)

    assert "### DATOS ESTRUCTURADOS (AGREGACIONES SQL)" in context.formatted_prompt_context
    assert "Hospital Salvador" in context.formatted_prompt_context
    assert "45000000" in context.formatted_prompt_context
    assert context.structured_data == sql_items


def test_context_builder_enforces_token_budget():
    # Very small budget (e.g. 50 tokens)
    builder = SecureContextBuilder(token_budget=50)

    long_items = [
        {
            "licitacion_id": f"LIC-{i}",
            "titulo": f"Titulo largo {i}",
            "chunk_text": "Texto repetitivo que ocupa muchos tokens en el contexto compilado. " * 10,
            "score": 0.9 - (i * 0.05),
        }
        for i in range(10)
    ]

    sources = [
        Source(id=f"LIC-{i}", source_type="tender", title=f"Titulo {i}")
        for i in range(10)
    ]

    retrieval_result = RetrievalResult(
        strategy_used=RetrievalStrategy.SEMANTIC,
        items=long_items,
        sources=sources,
        total_results=10,
    )

    context = builder.build_context("prueba presupuesto", retrieval_result, max_tokens=60)

    # The resulting token estimate should be bounded
    assert context.token_estimate <= 120  # Allows small header overhead but cuts candidate items
    # Should not include all 10 items because budget ran out
    assert "LIC-9" not in context.formatted_prompt_context


def test_context_builder_empty_retrieval():
    builder = SecureContextBuilder()
    empty_result = RetrievalResult(
        strategy_used=RetrievalStrategy.DIRECT,
        items=[],
        sources=[],
        total_results=0,
    )

    context = builder.build_context("sin resultados", empty_result)
    assert "No se encontraron registros ni documentos relevantes" in context.formatted_prompt_context
    assert context.sources == []
