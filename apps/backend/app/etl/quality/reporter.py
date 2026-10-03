"""Concrete data quality reporter for the ETL pipeline (Fase 3.10).

The ETL pipeline exposes a ``quality_reporter`` hook that is invoked after every
run with the coarse :class:`app.etl.models.ETLMetrics`. This module provides a
concrete implementation, :class:`DataQualityReporter`, that:

* derives the domain :class:`QualityMetrics` from those counters,
* optionally evaluates :class:`QualityRule` checks against a sample of the
  transformed payloads (when provided),
* stores the last report in memory so tests/exports can inspect it,
* emits structured log lines for observability.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.etl.models import ETLMetrics, IngestionRunContext
from app.etl.quality.metrics import QualityMetrics, metrics_from_etl
from app.etl.quality.rules import QualityReport, QualityRule, evaluate_rules

logger = logging.getLogger(__name__)


class DataQualityReporter:
    """Concrete ``QualityReporter`` that computes and records quality metrics.

    Attributes
    ----------
    reports
        Every emitted report (in ingestion order). Tests and exports can
        inspect this to verify behaviour.
    rules
        Optional per-entity quality rules applied against transformed payloads
        before they are stored. Keyed by entity name.
    """

    def __init__(
        self,
        *,
        rules: dict[str, list[QualityRule]] | None = None,
        on_report: Callable[[QualityMetrics], None] | None = None,
    ) -> None:
        self.rules = rules or {}
        self.on_report = on_report
        self.reports: list[QualityMetrics] = []

    @property
    def last_report(self) -> QualityMetrics | None:
        return self.reports[-1] if self.reports else None

    def emit(
        self,
        run: IngestionRunContext,
        metrics: ETLMetrics,
    ) -> None:
        """Compute and store quality metrics for an ingestion run."""
        derived = metrics_from_etl(
            metrics,
            source=run.source,
            resource=run.resource,
            ingestion_run_id=run.ingestion_run_id,
        )
        self.reports.append(derived)
        logger.info(
            "quality metrics for run=%s source=%s resource=%s rate=%s "
            "received=%d valid=%d invalid=%d duplicates=%d errors=%d",
            run.ingestion_run_id,
            run.source,
            run.resource,
            derived.quality_rate,
            derived.received,
            derived.valid,
            derived.invalid,
            derived.duplicates,
            derived.errors,
        )
        if self.on_report is not None:
            self.on_report(derived)

    # ------------------------------------------------------------------ #
    # Rule evaluation (optional, per entity)
    # ------------------------------------------------------------------ #
    def evaluate_payload_quality(
        self,
        entity: str,
        payload: dict[str, Any],
    ) -> QualityReport:
        """Evaluate configured quality rules for an entity against a payload."""
        rules = self.rules.get(entity, [])
        return evaluate_rules(payload, rules)


__all__ = ["DataQualityReporter"]
