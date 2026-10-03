from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

from app.integrations.chilecompra.exceptions import ChileCompraError

T = TypeVar("T")

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def is_retryable_status(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUSES


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    retry_delay: float,
    retryable_exceptions: tuple[type[Exception], ...],
) -> T:
    attempts = max(1, max_retries)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retryable_exceptions as exc:  # type: ignore[misc]
            last_error = exc
            if attempt >= attempts:
                raise
            await asyncio.sleep(retry_delay)

    raise ChileCompraError("Retry loop exhausted") from last_error
