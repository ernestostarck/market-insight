"""Unit tests for LLMGateway and providers (Fase 9.11)."""

from unittest.mock import AsyncMock

import pytest

from app.ai.contracts import Context, MessageRole, Source
from app.ai.llm.base import LLMProvider, LLMTimeoutError, RateLimitError
from app.ai.llm.gateway import LLMGateway
from app.ai.llm.models import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMMessage,
    LLMRole,
    TokenUsage,
)
from app.ai.llm.providers.local import LocalLLMProvider


@pytest.mark.asyncio
async def test_local_llm_provider_deterministic():
    provider = LocalLLMProvider()

    req = LLMCompletionRequest(
        messages=[
            LLMMessage(role=LLMRole.SYSTEM, content="System prompt"),
            LLMMessage(
                role=LLMRole.USER,
                content="[Fuente: licitacion 1234-56-LP24] Adquisicion de ambulancias por $45.000.000 CLP.\n\nPregunta: Cuanto costo?",
            ),
        ]
    )

    resp = await provider.complete(req)
    assert resp.provider == "local"
    assert "local-deterministic" in resp.model
    assert resp.usage.total_tokens > 0
    assert "1234-56-LP24" in resp.content
    assert "$45.000.000 CLP" in resp.content


@pytest.mark.asyncio
async def test_llm_gateway_generate_response():
    gateway = LLMGateway(primary_provider="local", fallback_provider="local")

    context = Context(
        formatted_prompt_context="### CONTEXT - UNTRUSTED DATA BEGIN ###\n[Fuente: licitacion 100-20-LP24] Hospital San Jose compra insumos por $10.000.000 CLP.\n### CONTEXT - UNTRUSTED DATA END ###",
        sources=[
            Source(
                id="100-20-LP24",
                source_type="tender",
                title="Compra de insumos",
            )
        ],
        token_estimate=50,
    )

    chat_message = await gateway.generate_response(
        user_query="¿Qué compró el Hospital San José?",
        context=context,
    )

    assert chat_message.role == MessageRole.ASSISTANT
    assert chat_message.content != ""
    assert chat_message.latency_ms is not None
    assert chat_message.latency_ms > 0
    assert "sources" in chat_message.metadata
    assert len(chat_message.metadata["sources"]) == 1
    assert chat_message.metadata["sources"][0]["id"] == "100-20-LP24"


@pytest.mark.asyncio
async def test_llm_gateway_retries_transient_errors():
    flaky_provider = AsyncMock(spec=LLMProvider)
    # Fails twice with RateLimitError, then succeeds
    successful_resp = LLMCompletionResponse(
        content="Respuesta recuperada tras reintento",
        model="mock-gpt",
        provider="mock",
        usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
    )
    flaky_provider.complete.side_effect = [
        RateLimitError("Rate limit exceeded 429"),
        RateLimitError("Rate limit exceeded 429"),
        successful_resp,
    ]

    gateway = LLMGateway(
        providers={"mock": flaky_provider},
        primary_provider="mock",
        fallback_provider=None,
        max_retries=3,
        retry_delay_base=0.01,  # Fast for unit tests
    )

    req = LLMCompletionRequest(
        messages=[LLMMessage(role=LLMRole.USER, content="Hola")]
    )
    result = await gateway.complete(req)

    assert result.content == "Respuesta recuperada tras reintento"
    assert flaky_provider.complete.call_count == 3


@pytest.mark.asyncio
async def test_llm_gateway_fallback_on_exhausted_retries():
    failing_provider = AsyncMock(spec=LLMProvider)
    failing_provider.complete.side_effect = LLMTimeoutError("Request timed out")

    fallback_provider = AsyncMock(spec=LLMProvider)
    fallback_provider.complete.return_value = LLMCompletionResponse(
        content="Respuesta de respaldo",
        model="fallback-model",
        provider="fallback",
    )

    gateway = LLMGateway(
        providers={"primary": failing_provider, "backup": fallback_provider},
        primary_provider="primary",
        fallback_provider="backup",
        max_retries=1,
        retry_delay_base=0.01,
    )

    req = LLMCompletionRequest(
        messages=[LLMMessage(role=LLMRole.USER, content="Consulta")]
    )
    result = await gateway.complete(req)

    assert result.content == "Respuesta de respaldo"
    assert result.provider == "fallback"
    assert failing_provider.complete.call_count == 2  # 1 initial + 1 retry
    assert fallback_provider.complete.call_count == 1


def test_llm_gateway_provider_registration():
    local = LocalLLMProvider()
    gateway = LLMGateway(providers={"local": local})

    assert gateway.get_provider("local") is local

    with pytest.raises(KeyError, match="not registered"):
        gateway.get_provider("unknown_provider")
