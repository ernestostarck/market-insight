"""Data contracts and schemas for the LLM Gateway (Fase 9.11)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMRole(str, Enum):
    """Role of the message participant."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    """Message sent to an LLM provider."""

    model_config = ConfigDict(frozen=True)

    role: str | LLMRole = Field(..., description="Message role: system, user, assistant.")
    content: str = Field(..., description="Text content of the message.")


class TokenUsage(BaseModel):
    """Token consumption accounting."""

    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @property
    def input_tokens(self) -> int:
        return self.prompt_tokens

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens


class LLMCompletionRequest(BaseModel):
    """Normalized request passed to an LLMProvider."""

    messages: list[LLMMessage] = Field(..., description="Chronological conversation turns.")
    model: str | None = Field(default=None, description="Target model name (uses provider default if None).")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature.")
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="Maximum completion tokens.")
    timeout_seconds: float = Field(default=30.0, gt=0.0, description="Timeout in seconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom tracking metadata.")


class LLMCompletionResponse(BaseModel):
    """Normalized completion response returned by an LLMProvider."""

    content: str = Field(..., description="Generated text completion.")
    model: str = Field(..., description="Model that produced the completion.")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token usage metrics.")
    latency_ms: float = Field(default=0.0, description="Latency in milliseconds.")
    provider: str = Field(..., description="Provider name: anthropic, openai, local.")
    finish_reason: str = Field(default="stop", description="Completion stop reason.")
