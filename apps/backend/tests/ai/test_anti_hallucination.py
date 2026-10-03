"""Unit tests for AntiHallucinationEngine (Fase 9.17)."""

from unittest.mock import AsyncMock

import pytest

from app.ai.anti_hallucination import AntiHallucinationEngine
from app.ai.contracts import (
    ChatMessage,
    Context,
    MessageRole,
    RetrievalResult,
    RetrievalStrategy,
    Source,
)
from app.ai.grounding_validator import INSUFFICIENT_EVIDENCE_FALLBACK
from app.ai.interfaces import LLMGateway


def test_verify_claims_flags_unsupported_numbers_and_codes():
    engine = AntiHallucinationEngine()

    context = Context(
        formatted_prompt_context=(
            "### CONTEXT - UNTRUSTED DATA BEGIN ###\n"
            "[Fuente: licitacion 1234-56-LP24] Gasto real de $50.000.000 CLP en 2024.\n"
            "### CONTEXT - UNTRUSTED DATA END ###"
        ),
        sources=[
            Source(
                id="1234-56-LP24",
                source_type="tender",
                title="Licitación Real",
                snippet="Gasto real de $50.000.000 CLP en 2024",
            )
        ],
    )

    # Clean answer
    clean_ans = "La licitación 1234-56-LP24 tuvo un gasto de $50.000.000 CLP en 2024."
    clean_res = engine.verify_claims(clean_ans, context)
    assert clean_res.is_valid is True
    assert clean_res.unsupported_claims == []

    # Hallucinated answer (invented number $999.000.000 and fake code 9999-99-LR25)
    hallucinated_ans = "La licitación 9999-99-LR25 gastó $999.000.000 CLP en el año 2024."
    fake_res = engine.verify_claims(hallucinated_ans, context)
    assert fake_res.is_valid is False
    assert "$999.000.000" in fake_res.unsupported_claims
    assert "9999-99-LR25" in fake_res.unsupported_claims
    assert "number/currency" in fake_res.discrepancy_types
    assert "tender_code" in fake_res.discrepancy_types


@pytest.mark.asyncio
async def test_sanitize_or_regenerate_passes_clean_answer_without_call():
    mock_gateway = AsyncMock(spec=LLMGateway)
    engine = AntiHallucinationEngine()

    context = Context(
        formatted_prompt_context="Hospital Central compró ambulancias por $40.000.000 CLP.",
        sources=[],
    )
    retrieval = RetrievalResult(strategy_used=RetrievalStrategy.DIRECT, total_results=1)

    clean_ans = "Hospital Central compró ambulancias por $40.000.000 CLP."
    final_ans, verification, was_regen = await engine.sanitize_or_regenerate(
        user_query="¿Cuánto gastó el Hospital Central?",
        initial_answer=clean_ans,
        context=context,
        retrieval_result=retrieval,
        llm_gateway=mock_gateway,
    )

    assert final_ans == clean_ans
    assert verification.is_valid is True
    assert was_regen is False
    mock_gateway.generate_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_sanitize_or_regenerate_resolves_hallucination_with_one_shot_regen():
    mock_gateway = AsyncMock(spec=LLMGateway)
    # The regenerated response removes the hallucinated number and gives the grounded statement
    mock_gateway.generate_response.return_value = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="La licitación 1234-56-LP24 se adjudicó a Tecnologías Médicas por $20.000.000 CLP.",
    )

    engine = AntiHallucinationEngine(max_regeneration_attempts=1)

    context = Context(
        formatted_prompt_context="[Fuente: licitacion 1234-56-LP24] Tecnologías Médicas por $20.000.000 CLP.",
        sources=[Source(id="1234-56-LP24", source_type="tender", title="Licitación")],
    )
    retrieval = RetrievalResult(strategy_used=RetrievalStrategy.HYBRID, total_results=1)

    hallucinated_ans = "Se adjudicaron $500.000.000 CLP en la licitación 1234-56-LP24."

    final_ans, verification, was_regen = await engine.sanitize_or_regenerate(
        user_query="¿Cuál fue el monto?",
        initial_answer=hallucinated_ans,
        context=context,
        retrieval_result=retrieval,
        llm_gateway=mock_gateway,
    )

    assert was_regen is True
    assert "$20.000.000 CLP" in final_ans
    assert verification.is_valid is True
    mock_gateway.generate_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_sanitize_or_regenerate_falls_back_to_insufficient_evidence():
    mock_gateway = AsyncMock(spec=LLMGateway)
    # The regenerated response STILL hallucinates
    mock_gateway.generate_response.return_value = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="Insisto en que fueron $888.000.000 CLP.",
    )

    engine = AntiHallucinationEngine(max_regeneration_attempts=1)

    context = Context(
        formatted_prompt_context="Datos sobre insumos básicos por $500.000 CLP.",
        sources=[],
    )
    retrieval = RetrievalResult(strategy_used=RetrievalStrategy.DIRECT, total_results=1)

    initial_hallucination = "El monto fue de $777.000.000 CLP."

    final_ans, _verification, was_regen = await engine.sanitize_or_regenerate(
        user_query="¿Monto total?",
        initial_answer=initial_hallucination,
        context=context,
        retrieval_result=retrieval,
        llm_gateway=mock_gateway,
    )

    assert was_regen is True
    assert final_ans == INSUFFICIENT_EVIDENCE_FALLBACK
