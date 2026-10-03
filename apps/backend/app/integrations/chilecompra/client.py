from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.exceptions import (
    ChileCompraAPIError,
    ChileCompraAuthenticationError,
    ChileCompraError,
    ChileCompraNotFoundError,
    ChileCompraRateLimitError,
    ChileCompraTimeoutError,
    ChileCompraValidationError,
)
from app.integrations.chilecompra.retry import is_retryable_status, retry_async


@dataclass(slots=True)
class ChileCompraHTTPResponse:
    status_code: int
    headers: dict[str, str]
    payload: dict[str, Any] | list[Any] | str | None


class ChileCompraHTTPClient:
    """HTTP client that wraps the official ChileCompra API."""

    def __init__(self, config: ChileCompraConfig) -> None:
        self._config = config

    def _base_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "MarketInsight/0.1.0",
        }

    def _base_params(self, params: Mapping[str, str] | None = None) -> dict[str, str]:
        merged = {"ticket": self._config.api_ticket}
        if params:
            merged.update({key: value for key, value in params.items() if value})
        return merged

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json: Any | None = None,
    ) -> ChileCompraHTTPResponse:
        async def do_request() -> ChileCompraHTTPResponse:
            try:
                async with httpx.AsyncClient(
                    base_url=self._config.api_url,
                    headers=self._base_headers(),
                    timeout=self._config.timeout,
                ) as client:
                    response = await client.request(
                        method,
                        path,
                        params=self._base_params(params),
                        json=json,
                    )
            except httpx.TimeoutException as exc:
                raise ChileCompraTimeoutError("ChileCompra request timed out") from exc
            except httpx.RequestError as exc:
                raise ChileCompraAPIError("ChileCompra request failed") from exc

            if response.status_code == 401 or response.status_code == 403:
                raise ChileCompraAuthenticationError(
                    f"ChileCompra rejected the ticket with status {response.status_code}"
                )
            if response.status_code == 404:
                raise ChileCompraNotFoundError("ChileCompra resource not found")
            if response.status_code == 400:
                raise ChileCompraValidationError("ChileCompra rejected the request")
            if response.status_code == 429:
                raise ChileCompraRateLimitError("ChileCompra rate limit reached")
            if is_retryable_status(response.status_code):
                raise ChileCompraAPIError(
                    f"ChileCompra returned retryable status {response.status_code}"
                )

            if response.status_code >= 400:
                # Never use raise_for_status(): its message embeds the URL, ticket included.
                raise ChileCompraAPIError(f"ChileCompra returned status {response.status_code}")
            payload: dict[str, Any] | list[Any] | str | None
            try:
                payload = response.json()
            except ValueError:
                payload = response.text

            return ChileCompraHTTPResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                payload=payload,
            )

        return await retry_async(
            do_request,
            max_retries=self._config.max_retries,
            retry_delay=self._config.retry_delay,
            retryable_exceptions=(
                ChileCompraAPIError,
                ChileCompraTimeoutError,
                ChileCompraRateLimitError,
            ),
        )

    async def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        response = await self.request("GET", path, params=params)
        if isinstance(response.payload, dict | list):
            return response.payload
        raise ChileCompraValidationError("ChileCompra response did not contain JSON")
