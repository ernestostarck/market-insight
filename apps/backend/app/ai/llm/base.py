"""Base interfaces and exceptions for LLM providers (Fase 9.11)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.llm.models import LLMCompletionRequest, LLMCompletionResponse


class LLMProviderError(RuntimeError):
    """Base exception for errors during LLM communication."""


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider request times out."""


class RateLimitError(LLMProviderError):
    """Raised when an LLM provider rate limit is exceeded."""


class LLMProvider(ABC):
    """Abstract provider interface decoupling MercadoInsight from specific LLM vendors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'anthropic', 'openai', 'local')."""

    @abstractmethod
    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        """Execute completion request and return normalized response."""
