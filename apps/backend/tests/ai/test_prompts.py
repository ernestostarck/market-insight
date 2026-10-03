"""Unit tests for Prompt Engineering templates and hyperparameters (Fase 9.12)."""

from app.ai.prompts.templates import (
    SYSTEM_PROMPT_V1,
    get_task_hyperparameters,
    render_guardrail_prompt,
    render_rag_prompt,
    render_sql_prompt,
)


def test_system_prompt_v1_contains_essential_guidelines():
    prompt = SYSTEM_PROMPT_V1
    assert "MercadoInsight AI" in prompt
    assert "ChileCompra" in prompt or "Mercado Público" in prompt
    assert "ÚNICAMENTE" in prompt
    assert "No dispongo de información suficiente" in prompt
    assert "[Fuente: {tipo} {id}]" in prompt
    assert "juicios de valor" in prompt.lower()


def test_render_rag_prompt():
    context = "### CONTEXT - UNTRUSTED DATA BEGIN ###\n[Fuente: licitacion 123-4-LP24] Licitacion de prueba\n### CONTEXT - UNTRUSTED DATA END ###"
    query = "¿Cuál es el código de licitación?"

    rendered = render_rag_prompt(context, query)
    assert context in rendered
    assert query in rendered
    assert "[Fuente: {tipo} {id}]" in rendered


def test_render_sql_prompt():
    query = "Top 5 proveedores con mayor gasto en 2024"
    rendered = render_sql_prompt(query)
    assert query in rendered
    assert "dm_compras" in rendered
    assert "SELECT" in rendered
    assert "LIMIT" in rendered


def test_render_guardrail_prompt():
    context = "El comprador es Hospital del Salvador."
    answer = "El comprador es el Hospital del Salvador [Fuente: tender 1]."
    rendered = render_guardrail_prompt(context, answer)
    assert context in rendered
    assert answer in rendered
    assert "is_grounded" in rendered
    assert "grounding_score" in rendered


def test_get_task_hyperparameters():
    rag_params = get_task_hyperparameters("rag_analytic")
    assert rag_params["temperature"] == 0.0
    assert rag_params["top_p"] == 0.95

    search_params = get_task_hyperparameters("semantic_search")
    assert search_params["temperature"] == 0.0

    exec_params = get_task_hyperparameters("executive_summary")
    assert exec_params["temperature"] > 0.0

    # Fallback to rag_analytic default on unknown task
    default_params = get_task_hyperparameters("unknown_task")
    assert default_params["temperature"] == 0.0
