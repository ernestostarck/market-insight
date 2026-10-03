"""OpenTelemetry distributed tracing setup and instrumentation (Fase 8.13).

Instruments FastAPI, outgoing HTTPX requests, and attaches correlation IDs
(request_id) to all active spans with W3C TraceContext propagation.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from app.core.context import get_request_id
from app.core.settings import Settings, get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_TELEMETRY_INITIALIZED = False


def setup_telemetry(app: FastAPI | None = None, settings: Settings | None = None) -> bool:
    """Configure OpenTelemetry TracerProvider and instrument FastAPI and HTTPX."""
    global _TELEMETRY_INITIALIZED

    current_settings = settings or get_settings()
    if not current_settings.otel_enabled:
        logger.info("OpenTelemetry is disabled via configuration.")
        return False

    if _TELEMETRY_INITIALIZED:
        return True

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        resource = Resource.create({
            "service.name": current_settings.otel_service_name,
            "service.version": current_settings.app_version,
            "deployment.environment": current_settings.environment,
        })

        provider = TracerProvider(resource=resource)

        # If an OTLP collector endpoint is configured, export spans to it
        if current_settings.otel_exporter_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                otlp_exporter = OTLPSpanExporter(
                    endpoint=current_settings.otel_exporter_endpoint, insecure=True
                )
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(
                    "OTLP Span Exporter connected to %s",
                    current_settings.otel_exporter_endpoint,
                )
            except Exception as otlp_err:  # noqa: BLE001
                logger.warning("Could not initialize OTLP exporter: %s", otlp_err)
        elif current_settings.debug and os.getenv("OTEL_CONSOLE_EXPORTER", "").lower() in ("true", "1"):
            # In debug mode without collector, export summary to console only if explicitly enabled
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)

        # Instrument HTTPX for outbound requests (ChileCompra, external APIs)
        HTTPXClientInstrumentor().instrument()

        # Instrument FastAPI if app instance passed
        if app is not None:
            def server_request_hook(span: Any, scope: dict[str, Any]) -> None:
                if span and span.is_recording():
                    req_id = get_request_id()
                    if req_id and req_id != "-":
                        span.set_attribute("app.request_id", req_id)
                        span.set_attribute("correlation_id", req_id)

            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=provider,
                server_request_hook=server_request_hook,
            )

        _TELEMETRY_INITIALIZED = True
        logger.info("OpenTelemetry instrumentation completed successfully.")
        return True
    except Exception as err:  # noqa: BLE001
        logger.warning("Failed to initialize OpenTelemetry: %s", err)
        return False


def get_current_trace_id() -> str | None:
    """Return the current active OpenTelemetry trace_id as a hex string, if any."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except (ImportError, AttributeError, ValueError):
        return None
    return None
