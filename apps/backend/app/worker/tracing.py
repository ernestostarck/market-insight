"""Carry the API's X-Request-ID across the Celery boundary.

A request that enqueues work (ETL sync, NLP batch) would otherwise lose its
correlation ID at the broker: worker logs, Sentry events and spans would show
``request_id="-"``. The ID travels as a message header, set on publish and
restored into the worker's context for the duration of the task.
"""

from __future__ import annotations

from typing import Any

from celery.signals import before_task_publish, task_postrun, task_prerun

from app.core.context import get_request_id, reset_request_id, set_request_id

REQUEST_ID_HEADER = "x_request_id"

# task_id -> contextvar token, so postrun resets exactly what prerun set.
_tokens: dict[str, Any] = {}


@before_task_publish.connect
def _inject_request_id(headers: dict[str, Any] | None = None, **_: Any) -> None:
    request_id = get_request_id()
    if headers is not None and request_id:
        headers[REQUEST_ID_HEADER] = request_id


@task_prerun.connect
def _restore_request_id(task_id: str | None = None, task: Any = None, **_: Any) -> None:
    request_id = getattr(getattr(task, "request", None), REQUEST_ID_HEADER, None)
    if task_id and request_id:
        _tokens[task_id] = set_request_id(request_id)


@task_postrun.connect
def _clear_request_id(task_id: str | None = None, **_: Any) -> None:
    token = _tokens.pop(task_id, None) if task_id else None
    if token is not None:
        reset_request_id(token)
