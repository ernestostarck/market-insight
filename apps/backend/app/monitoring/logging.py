"""Logging monitoring module exposing structured JSON logging utilities.

Re-exports and extends application logging configurations for the monitoring namespace.
"""

from __future__ import annotations

import logging

from app.core.logging import (
    JSONFormatter,
    configure_logging,
)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger instance configured for the given name."""
    return logging.getLogger(name)


__all__ = [
    "JSONFormatter",
    "configure_logging",
    "get_logger",
]
