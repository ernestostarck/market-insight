"""OpenAI LLM Provider for MercadoInsight AI (Fase 9.11)."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from app.ai.llm.base import (
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    RateLimitError,
)
from app.ai.llm.models import LLMCompletionRequest, LLMCompletionResponse, TokenUsage


class OpenAIProvider(LLMProvider):
    """Provider integrating OpenAI models (GPT-4o, GPT-4o-mini) via standard HTTP REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o",
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "openai"

    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        if not self._api_key:
            raise LLMProviderError("OpenAI API key is missing. Set OPENAI_API_KEY.")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 429:
                raise RateLimitError(f"OpenAI rate limit exceeded: {response.text}")

            if response.status_code >= 400:
                raise LLMProviderError(
                    f"OpenAI API error ({response.status_code}): {response.text}"
                )

            data = response.json()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            choice = data["choices"][0]
            content = choice["message"]["content"]
            raw_usage = data.get("usage", {})

            return LLMCompletionResponse(
                content=content,
                model=data.get("model", request.model or self._default_model),
                usage=TokenUsage(
                    prompt_tokens=raw_usage.get("prompt_tokens", 0),
                    completion_tokens=raw_usage.get("completion_tokens", 0),
                    total_tokens=raw_usage.get("total_tokens", 0),
                ),
                latency_ms=round(elapsed_ms, 2),
                provider=self.name,
            )

        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI request timed out after {request.timeout_seconds}s") from exc
        except (RateLimitError, LLMProviderError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"Unexpected error communicating with OpenAI: {exc}") from exc
