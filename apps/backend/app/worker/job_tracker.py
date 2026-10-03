"""Redis-backed job tracker and idempotency store for the NLP worker (Fase 6.20)."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 86400 * 7  # 7 days


class JobTracker:
    """Synchronous Redis client for Celery worker processes with graceful fallback."""

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            settings = get_settings()
            try:
                self._redis = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("failed to connect to Redis for job tracking: %s", exc)
                self._redis = None

    def get_idempotent_result(self, idempotency_key: str) -> dict[str, Any] | None:
        if self._redis is None:
            return None
        try:
            cached = self._redis.get(f"nlp:idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis read error for idempotency_key '%s': %s", idempotency_key, exc)
        return None

    def record_job_start(self, task_id: str, idempotency_key: str, licitacion_id: int) -> None:
        if self._redis is None:
            return
        try:
            payload = {
                "task_id": task_id,
                "idempotency_key": idempotency_key,
                "licitacion_id": licitacion_id,
                "status": "running",
            }
            self._redis.set(f"nlp:job:{task_id}", json.dumps(payload), ex=_DEFAULT_TTL)
        except Exception as exc:
            logger.warning("Redis write error for job start '%s': %s", task_id, exc)

    def record_job_success(
        self,
        task_id: str,
        idempotency_key: str,
        result: dict[str, Any],
        duration_seconds: float,
    ) -> None:
        if self._redis is None:
            return
        try:
            payload = {
                "task_id": task_id,
                "idempotency_key": idempotency_key,
                "status": "succeeded",
                "duration_seconds": duration_seconds,
                "result": result,
            }
            raw = json.dumps(payload)
            self._redis.set(f"nlp:job:{task_id}", raw, ex=_DEFAULT_TTL)
            self._redis.set(f"nlp:idempotency:{idempotency_key}", raw, ex=_DEFAULT_TTL)
        except Exception as exc:
            logger.warning("Redis write error for job success '%s': %s", task_id, exc)

    def record_job_failure(
        self,
        task_id: str,
        idempotency_key: str,
        error: dict[str, Any],
        duration_seconds: float,
    ) -> None:
        if self._redis is None:
            return
        try:
            payload = {
                "task_id": task_id,
                "idempotency_key": idempotency_key,
                "status": "failed",
                "duration_seconds": duration_seconds,
                "error": error,
            }
            self._redis.set(f"nlp:job:{task_id}", json.dumps(payload), ex=_DEFAULT_TTL)
        except Exception as exc:
            logger.warning("Redis write error for job failure '%s': %s", task_id, exc)

    def get_job_state(self, task_id: str) -> dict[str, Any] | None:
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(f"nlp:job:{task_id}")
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis read error for job state '%s': %s", task_id, exc)
        return None
