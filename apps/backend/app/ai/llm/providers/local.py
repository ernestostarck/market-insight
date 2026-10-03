"""Deterministic Local / Mock LLM Provider (Fase 9.11).

Provides an offline, deterministic completion engine for testing, development,
and local fallback without requiring external API keys.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from app.ai.llm.base import LLMProvider
from app.ai.llm.models import LLMCompletionRequest, LLMCompletionResponse, TokenUsage


class LocalLLMProvider(LLMProvider):
    """Local provider that synthesizes responses deterministically from context."""

    def __init__(
        self,
        custom_responder: Callable[[LLMCompletionRequest], str] | None = None,
        default_model: str = "local-deterministic-v1",
    ) -> None:
        self._responder = custom_responder
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "local"

    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        start_time = time.perf_counter()

        if self._responder is not None:
            content = self._responder(request)
        else:
            # Extract user message
            user_msg = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
            system_msg = next((m.content for m in request.messages if m.role == "system"), "")

            # Simple deterministic evidence synthesis
            if "UNTRUSTED DATA BEGIN" in user_msg or "UNTRUSTED DATA BEGIN" in system_msg or "Fuente:" in user_msg:
                content = (
                    "En base a los antecedentes verificados en el sistema de Mercado Público, "
                    f"se identificaron los registros pertinentes: {user_msg[:160]}. "
                    "Todos los datos cuantitativos y documentales corresponden a las fuentes oficiales auditadas."
                )
            else:
                content = (
                    f"Respuesta generada localmente para la consulta: '{user_msg[:60]}'. "
                    "El motor analítico ha procesado su solicitud con éxito."
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Estimate tokens
        prompt_chars = sum(len(m.content) for m in request.messages)
        prompt_tokens = max(1, prompt_chars // 4)
        completion_tokens = max(1, len(content) // 4)

        return LLMCompletionResponse(
            content=content,
            model=request.model or self._default_model,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            latency_ms=round(elapsed_ms, 2),
            provider=self.name,
        )
