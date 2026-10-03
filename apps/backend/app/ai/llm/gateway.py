"""LLM Gateway orchestrating providers, retries, fallbacks, and monitoring (Fase 9.11)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import uuid4

from app.ai.contracts import ChatMessage, Context, MessageRole
from app.ai.interfaces import LLMGateway as LLMGatewayProtocol
from app.ai.llm.base import (
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    RateLimitError,
)
from app.ai.llm.models import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMMessage,
    LLMRole,
)
from app.ai.llm.providers.anthropic import AnthropicProvider
from app.ai.llm.providers.local import LocalLLMProvider
from app.ai.llm.providers.openai import OpenAIProvider
from app.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_GROUNDED_SYSTEM_PROMPT = """Eres MercadoInsight AI, un asistente analítico especializado en compras públicas de Chile (ChileCompra / Mercado Público).
Reglas fundamentales:
1. Responde únicamente basándote en la información verificable provista en el CONTEXTO.
2. Si los datos del contexto no son suficientes para responder la pregunta, indícalo con total transparencia.
3. No inventes cifras, RUTs, licitaciones, montos ni fechas.
4. Cita siempre las fuentes y códigos de licitación pertinentes presentes en el contexto.
"""


class LLMGateway(LLMGatewayProtocol):
    """Production-grade LLM Gateway with provider abstraction, retries, and fallback."""

    def __init__(
        self,
        providers: dict[str, LLMProvider] | None = None,
        primary_provider: str | None = None,
        fallback_provider: str | None = "local",
        settings: Settings | None = None,
        max_retries: int | None = None,
        retry_delay_base: float = 0.5,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_retries = (
            max_retries if max_retries is not None else self.settings.llm_max_retries
        )
        self.retry_delay_base = retry_delay_base
        self.primary_provider_name = (
            primary_provider or self.settings.llm_provider or "local"
        ).lower()
        self.fallback_provider_name = fallback_provider.lower() if fallback_provider else None

        # Initialize providers if not explicitly injected
        if providers is not None:
            self._providers = {k.lower(): v for k, v in providers.items()}
        else:
            self._providers = self._init_default_providers()

    def _init_default_providers(self) -> dict[str, LLMProvider]:
        """Instantiate available providers based on settings."""
        providers: dict[str, LLMProvider] = {
            "local": LocalLLMProvider(default_model="local-deterministic"),
        }

        if self.settings.openai_api_key:
            providers["openai"] = OpenAIProvider(
                api_key=self.settings.openai_api_key,
                default_model=self.settings.llm_model_name
                if "gpt" in self.settings.llm_model_name
                else "gpt-4o-mini",
                timeout=self.settings.llm_timeout_seconds,
            )

        if self.settings.anthropic_api_key:
            providers["anthropic"] = AnthropicProvider(
                api_key=self.settings.anthropic_api_key,
                default_model=self.settings.llm_model_name
                if "claude" in self.settings.llm_model_name
                else "claude-3-5-sonnet-latest",
                timeout=self.settings.llm_timeout_seconds,
            )

        return providers

    def get_provider(self, provider_name: str) -> LLMProvider:
        """Retrieve a registered provider by name."""
        name = provider_name.lower()
        if name not in self._providers:
            raise KeyError(
                f"Provider '{name}' is not registered. Available: {list(self._providers.keys())}"
            )
        return self._providers[name]

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Register or override an LLM provider."""
        self._providers[name.lower()] = provider

    async def complete(
        self,
        request: LLMCompletionRequest,
        provider_name: str | None = None,
    ) -> LLMCompletionResponse:
        """Execute a completion request with exponential backoff and optional fallback."""
        target_provider_name = (provider_name or self.primary_provider_name).lower()
        provider = self.get_provider(target_provider_name)

        attempt = 0
        last_exception: Exception | None = None

        while attempt <= self.max_retries:
            try:
                logger.debug(
                    "Attempting LLM completion with provider '%s' (attempt %d/%d)",
                    target_provider_name,
                    attempt + 1,
                    self.max_retries + 1,
                )
                return await provider.complete(request)
            except (RateLimitError, LLMTimeoutError) as exc:
                last_exception = exc
                attempt += 1
                if attempt <= self.max_retries:
                    delay = self.retry_delay_base * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient error '%s' on provider '%s'. Retrying in %.2fs (attempt %d/%d)...",
                        exc,
                        target_provider_name,
                        delay,
                        attempt,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    break
            except LLMProviderError as exc:
                last_exception = exc
                logger.error(
                    "Non-retryable provider error on '%s': %s",
                    target_provider_name,
                    exc,
                )
                break

        # If primary failed and fallback is configured
        if (
            self.fallback_provider_name
            and self.fallback_provider_name != target_provider_name
            and self.fallback_provider_name in self._providers
        ):
            logger.warning(
                "Primary provider '%s' failed. Falling back to '%s'...",
                target_provider_name,
                self.fallback_provider_name,
            )
            fallback = self.get_provider(self.fallback_provider_name)
            return await fallback.complete(request)

        if last_exception:
            raise last_exception
        raise LLMProviderError(f"LLM request failed on provider '{target_provider_name}'")

    async def generate_response(
        self,
        user_query: str,
        context: Context,
        system_prompt: str | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> ChatMessage:
        """Generate an assistant message grounded in the provided context (LLMGateway protocol)."""
        start_time = time.perf_counter()

        sys_prompt = system_prompt or DEFAULT_GROUNDED_SYSTEM_PROMPT
        messages: list[LLMMessage] = [
            LLMMessage(role=LLMRole.SYSTEM, content=sys_prompt)
        ]

        if conversation_history:
            for prev_msg in conversation_history:
                role = (
                    LLMRole.USER
                    if prev_msg.role == MessageRole.USER
                    else LLMRole.ASSISTANT
                )
                messages.append(LLMMessage(role=role, content=prev_msg.content))

        # Format user prompt integrating context
        user_prompt_content = f"{context.formatted_prompt_context}\n\nPregunta del usuario:\n{user_query}"
        messages.append(LLMMessage(role=LLMRole.USER, content=user_prompt_content))

        request = LLMCompletionRequest(
            messages=messages,
            temperature=0.0,
            metadata={"query": user_query, "sources_count": len(context.sources)},
        )

        response = await self.complete(request)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        metadata: dict[str, Any] = {
            "sources": [s.model_dump() for s in context.sources],
            "provider": response.provider,
            "finish_reason": response.finish_reason,
        }

        return ChatMessage(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            content=response.content,
            model=response.model,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            latency_ms=latency_ms,
            metadata=metadata,
        )
