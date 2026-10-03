"""Anthropic LLM Provider for MercadoInsight AI (Fase 9.11)."""

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


class AnthropicProvider(LLMProvider):
    """Provider integrating Anthropic models (Claude 3.5 Sonnet / Haiku) via HTTP Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        default_model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "anthropic"

    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        if not self._api_key:
            raise LLMProviderError("Anthropic API key is missing. Set ANTHROPIC_API_KEY.")

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Extract system prompt if present (Anthropic separates system instructions from messages)
        system_prompts = [m.content for m in request.messages if m.role == "system"]
        system_content = "\n\n".join(system_prompts) if system_prompts else None

        conversation_turns = [
            {"role": ("assistant" if m.role == "assistant" else "user"), "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]

        payload: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": conversation_turns,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system_content:
            payload["system"] = system_content

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 429:
                raise RateLimitError(f"Anthropic rate limit exceeded: {response.text}")

            if response.status_code >= 400:
                raise LLMProviderError(
                    f"Anthropic API error ({response.status_code}): {response.text}"
                )

            data = response.json()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            content_blocks = data.get("content", [])
            text_response = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            raw_usage = data.get("usage", {})

            return LLMCompletionResponse(
                content=text_response,
                model=data.get("model", request.model or self._default_model),
                usage=TokenUsage(
                    prompt_tokens=raw_usage.get("input_tokens", 0),
                    completion_tokens=raw_usage.get("output_tokens", 0),
                    total_tokens=raw_usage.get("input_tokens", 0) + raw_usage.get("output_tokens", 0),
                ),
                latency_ms=round(elapsed_ms, 2),
                provider=self.name,
            )

        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Anthropic request timed out after {request.timeout_seconds}s") from exc
        except (RateLimitError, LLMProviderError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"Unexpected error communicating with Anthropic: {exc}") from exc
