from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import text

from app.api.deps.settings import Settings
from app.db.session import AsyncSessionLocal
from app.monitoring.metrics import CHILECOMPRA_PROBE_LATENCY_SECONDS, CHILECOMPRA_UP
from app.schemas.health import (
    DependencyDetail,
    LivenessResponse,
    ReadinessResponse,
)

logger = logging.getLogger(__name__)

# Track process startup time for uptime calculation
_PROCESS_START_TIME = time.time()


def get_uptime_seconds() -> float:
    """Return elapsed process uptime in seconds."""
    return round(time.time() - _PROCESS_START_TIME, 2)


class HealthChecker:
    """Evaluates service health and downstream dependencies."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def check_liveness(self) -> LivenessResponse:
        """Lightweight check verifying the process is running and answering."""
        return LivenessResponse(
            status="ok",
            service=self.settings.app_name,
            version=self.settings.app_version,
            uptime_seconds=get_uptime_seconds(),
        )

    async def check_postgres(self, timeout: float = 1.5) -> DependencyDetail:
        """Probe PostgreSQL connectivity and execute a lightweight ping."""
        start = time.perf_counter()
        try:
            async with AsyncSessionLocal() as session:
                await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=timeout)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(status="healthy", latency_ms=latency_ms)
        except TimeoutError:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(
                status="unhealthy",
                latency_ms=latency_ms,
                error=f"PostgreSQL probe timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning("PostgreSQL health check failed: %s", exc)
            return DependencyDetail(
                status="unhealthy",
                latency_ms=latency_ms,
                error=str(exc),
            )

    async def check_redis(self, timeout: float = 1.5) -> DependencyDetail:
        """Probe Redis connectivity via asynchronous ping."""
        start = time.perf_counter()
        client: aioredis.Redis | None = None
        try:
            client = aioredis.from_url(
                self.settings.redis_url,
                socket_connect_timeout=timeout,
                socket_timeout=timeout,
            )
            pong = await asyncio.wait_for(client.ping(), timeout=timeout)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if pong:
                return DependencyDetail(status="healthy", latency_ms=latency_ms)
            return DependencyDetail(
                status="unhealthy",
                latency_ms=latency_ms,
                error="Redis ping did not return True/PONG",
            )
        except TimeoutError:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(
                status="unhealthy",
                latency_ms=latency_ms,
                error=f"Redis probe timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning("Redis health check failed: %s", exc)
            return DependencyDetail(
                status="unhealthy",
                latency_ms=latency_ms,
                error=str(exc),
            )
        finally:
            if client is not None:
                await client.aclose()

    async def check_storage(self, timeout: float = 1.5) -> DependencyDetail:
        """Probe MinIO / S3 Object Storage availability."""
        start = time.perf_counter()
        try:
            # Run sync MinIO check inside a thread executor to avoid blocking event loop
            def _probe_minio() -> bool:
                from minio import Minio

                client = Minio(
                    endpoint=self.settings.minio_endpoint,
                    access_key=self.settings.minio_access_key,
                    secret_key=self.settings.minio_secret_key,
                    secure=False,
                )
                # list_buckets is lightweight and confirms authentication
                client.list_buckets()
                return True

            await asyncio.wait_for(asyncio.to_thread(_probe_minio), timeout=timeout)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(status="healthy", latency_ms=latency_ms)
        except TimeoutError:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(
                status="degraded",
                latency_ms=latency_ms,
                error=f"Storage probe timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug("Storage health check returned error: %s", exc)
            return DependencyDetail(
                status="degraded",
                latency_ms=latency_ms,
                error=str(exc),
            )

    async def check_chilecompra(self, timeout: float = 1.5) -> DependencyDetail:
        """Probe the external ChileCompra API and publish ``chilecompra_up``.

        This is technical reachability only. Whether the data is fresh is a
        separate question answered by ``data_freshness_seconds``.
        """
        detail = await self._probe_chilecompra(timeout)
        CHILECOMPRA_UP.set(1 if detail.status == "healthy" else 0)
        if detail.latency_ms is not None:
            CHILECOMPRA_PROBE_LATENCY_SECONDS.set(detail.latency_ms / 1000.0)
        return detail

    async def _probe_chilecompra(self, timeout: float) -> DependencyDetail:
        start = time.perf_counter()
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    self.settings.chilecompra_base_url,
                    follow_redirects=True,
                )
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                if resp.status_code < 500:
                    return DependencyDetail(status="healthy", latency_ms=latency_ms)
                return DependencyDetail(
                    status="degraded",
                    latency_ms=latency_ms,
                    error=f"ChileCompra returned HTTP {resp.status_code}",
                )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(
                status="degraded",
                latency_ms=latency_ms,
                error=f"ChileCompra external API unreachable: {exc}",
            )

    async def check_workers(self, timeout: float = 1.5) -> DependencyDetail:
        """Check Celery worker broker status."""
        start = time.perf_counter()
        try:
            # Check broker redis queue connection
            client = aioredis.from_url(
                self.settings.redis_url,
                socket_connect_timeout=timeout,
                socket_timeout=timeout,
            )
            await asyncio.wait_for(client.ping(), timeout=timeout)
            await client.aclose()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(status="healthy", latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return DependencyDetail(
                status="degraded",
                latency_ms=latency_ms,
                error=str(exc),
            )

    async def check_readiness(
        self,
        include_external: bool = False,
    ) -> tuple[ReadinessResponse, bool]:
        """
        Evaluate all core dependencies.
        Returns (ReadinessResponse, is_ready: bool).
        """
        # Run core probes concurrently
        probes: list[Any] = [
            self.check_postgres(),
            self.check_redis(),
            self.check_storage(),
            self.check_workers(),
        ]
        if include_external:
            probes.append(self.check_chilecompra())

        results = await asyncio.gather(*probes, return_exceptions=True)

        dependencies: dict[str, DependencyDetail] = {}

        # Handle postgres
        pg_res = results[0]
        if isinstance(pg_res, Exception):
            dependencies["postgres"] = DependencyDetail(
                status="unhealthy", error=str(pg_res)
            )
        else:
            dependencies["postgres"] = pg_res

        # Handle redis
        redis_res = results[1]
        if isinstance(redis_res, Exception):
            dependencies["redis"] = DependencyDetail(
                status="unhealthy", error=str(redis_res)
            )
        else:
            dependencies["redis"] = redis_res

        # Handle storage
        storage_res = results[2]
        if isinstance(storage_res, Exception):
            dependencies["storage"] = DependencyDetail(
                status="degraded", error=str(storage_res)
            )
        else:
            dependencies["storage"] = storage_res

        # Handle workers
        workers_res = results[3]
        if isinstance(workers_res, Exception):
            dependencies["workers"] = DependencyDetail(
                status="degraded", error=str(workers_res)
            )
        else:
            dependencies["workers"] = workers_res

        if include_external and len(results) > 4:
            cc_res = results[4]
            if isinstance(cc_res, Exception):
                dependencies["chilecompra"] = DependencyDetail(
                    status="degraded", error=str(cc_res)
                )
            else:
                dependencies["chilecompra"] = cc_res

        # Critical dependencies for readiness are PostgreSQL and Redis
        postgres_healthy = dependencies["postgres"].status == "healthy"
        redis_healthy = dependencies["redis"].status == "healthy"
        is_ready = postgres_healthy and redis_healthy

        response = ReadinessResponse(
            status="ready" if is_ready else "not_ready",
            service=self.settings.app_name,
            version=self.settings.app_version,
            environment=self.settings.environment,
            dependencies=dependencies,
        )

        return response, is_ready


async def run_chilecompra_probe(settings: Settings, interval_seconds: float = 60.0) -> None:
    """Keep ``chilecompra_up`` current for Prometheus, independent of who polls the API."""
    checker = HealthChecker(settings)
    while True:
        try:
            await checker.check_chilecompra(timeout=5.0)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("ChileCompra availability probe failed", exc_info=True)
        await asyncio.sleep(interval_seconds)
