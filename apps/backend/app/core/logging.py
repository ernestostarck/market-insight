from __future__ import annotations

import json
import logging
import logging.config
import re
from datetime import UTC, datetime

from app.core.context import get_request_id
from app.core.settings import get_settings

# Attributes every stdlib LogRecord carries. Anything else on a record came
# from `extra={...}` at the call site and should be surfaced in structured
# output instead of silently dropped.
_STANDARD_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

_SENSITIVE_KEYS = frozenset({
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "chilecompra_api_key",
    "authorization",
    "secret_key",
})


_SENSITIVE_KEY_TERMS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "ticket",
    "authorization",
    "cookie",
    "private_key",
)

REDACTED = "***REDACTED***"

# Secrets that reach a log line through free text (f-strings, exception
# messages, URLs) rather than through a well-named `extra` key.
_SECRET_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Authorization headers: "Bearer <jwt>" / "Basic <b64>"
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), rf"\1 {REDACTED}"),
    # key=value / key: value / "key": "value" where the key names a secret
    (
        re.compile(
            r"""(?i)(["']?[\w-]*(?:password|passwd|secret|token|api[_-]?key|ticket)[\w-]*["']?)"""
            r"""(\s*[=:]\s*)("[^"]*"|'[^']*'|[^\s,;&"'}\]]+)"""
        ),
        rf"\1\2{REDACTED}",
    ),
    # Credentials embedded in URLs: scheme://user:password@host or scheme://:password@host
    (re.compile(r"(://[^/\s:@]*:)([^@\s/]+)(@)"), rf"\1{REDACTED}\3"),
)


def is_sensitive_key(key: object) -> bool:
    clean = str(key).lower().replace("-", "_")
    return clean in _SENSITIVE_KEYS or any(term in clean for term in _SENSITIVE_KEY_TERMS)


def redact_text(text: str) -> str:
    """Mask secrets embedded in free text (tokens, passwords, API tickets, URL credentials)."""
    for pattern, replacement in _SECRET_TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_value(value: object) -> object:
    """Recursively redact nested structures: sensitive keys by name, strings by content."""
    if isinstance(value, dict):
        return {k: REDACTED if is_sensitive_key(k) else redact_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def _mask_value(val: object) -> object:
    if isinstance(val, str) and len(val) > 4:
        return f"{val[:2]}***{val[-2:]}"
    return REDACTED


class ContextFilter(logging.Filter):
    """Injects request-scoped and app-scoped context into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        settings = get_settings()
        record.app_name = settings.app_name
        record.environment = settings.environment
        record.request_id = get_request_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """Renders one JSON object per line - safe for log aggregators (Loki, ELK, CloudWatch)."""

    def format(self, record: logging.LogRecord) -> str:
        service_name = (
            getattr(record, "service", None)
            or getattr(record, "app_name", None)
            or "market-insight-backend"
        )

        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
            "service": service_name,
            "app_name": getattr(record, "app_name", service_name),
            "environment": getattr(record, "environment", None),
            "request_id": getattr(record, "request_id", "-"),
            "pipeline": getattr(record, "pipeline", None),
            "event": getattr(record, "event", None),
            "run_id": getattr(record, "run_id", None),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        # Format error attribute if provided or inferred
        error_val = getattr(record, "error", None)
        if error_val is not None:
            payload["error"] = redact_text(str(error_val))
        elif record.exc_info:
            payload["error"] = redact_text(self.formatException(record.exc_info))
        elif record.levelname in ("ERROR", "CRITICAL"):
            payload["error"] = redact_text(record.getMessage())

        # Extract extra fields passed to logger
        extra_data: dict[str, object] = {}
        for key, value in record.__dict__.items():
            if (
                key not in _STANDARD_RECORD_ATTRS
                and key not in payload
                and key not in (
                    "app_name",
                    "environment",
                    "request_id",
                    "service",
                    "pipeline",
                    "event",
                    "run_id",
                    "error",
                )
            ):
                if is_sensitive_key(key) and not isinstance(value, (int, float, bool, type(None))):
                    extra_data[key] = _mask_value(value) if isinstance(value, str) else REDACTED
                else:
                    extra_data[key] = redact_value(value)

        if extra_data:
            payload["extra"] = extra_data
            for k, v in extra_data.items():
                if k not in payload:
                    payload[k] = v

        if record.exc_info and "exception" not in payload:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        if record.stack_info:
            payload["stack"] = redact_text(self.formatStack(record.stack_info))

        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable single-line format for local development."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | rid=%(request_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record))


def _resolve_format(log_format: str, environment: str) -> str:
    if log_format == "auto":
        return "console" if environment == "development" else "json"
    return log_format


def build_logging_config() -> dict[str, object]:
    settings = get_settings()
    resolved_format = _resolve_format(settings.log_format, settings.environment)
    formatter_key = "json" if resolved_format == "json" else "console"
    level = settings.log_level.upper()
    sql_level = "INFO" if settings.log_sql else "WARNING"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context": {"()": ContextFilter},
        },
        "formatters": {
            "json": {"()": JSONFormatter},
            "console": {"()": ConsoleFormatter},
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": formatter_key,
                "filters": ["context"],
            },
        },
        "root": {
            "handlers": ["default"],
            "level": level,
        },
        "loggers": {
            # Route uvicorn's own loggers through our handler/formatter instead
            # of the colored default it installs before our config ever runs,
            # so every line - ours and uvicorn's - shares one format and one
            # request_id-aware filter.
            "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
            # Silenced: RequestIDMiddleware's "app.access" logger already emits
            # one richer line per request (with request_id and duration_ms).
            "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
            "sqlalchemy.engine": {
                "handlers": ["default"],
                "level": sql_level,
                "propagate": False,
            },
            "httpx": {"handlers": ["default"], "level": "WARNING", "propagate": False},
            "httpcore": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        },
    }


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging() -> None:
    """Configure app-wide logging: JSON outside dev, console in dev, request_id on every line."""
    logging.config.dictConfig(build_logging_config())
