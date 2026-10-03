"""Data quality metrics for the ETL pipeline (Fase 3.10).

Quality metrics quantify how well a single ingestion run performed in terms of
validity, completeness and duplication. They are derived from the coarse
:class:`app.etl.models.ETLMetrics` counters that the pipeline already tracks and
add the *quality rate* — the fraction of processed records that were valid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.etl.models import ETLMetrics


@dataclass(slots=True)
class QualityMetrics:
    """Domain-oriented quality metrics for one ingestion run.

    Attributes
    ----------
    received
        Total records received by the run.
    valid
        Records that passed validation and were accepted for transformation.
    invalid
        Records rejected by validation (quarantined).
    inserted
        New records written to the analytical store.
    updated
        Existing records whose payload changed and were updated.
    duplicates
        Records already present with an identical payload hash (skipped).
    errors
        Records that produced a load error or were failed.
    quality_rate
        Ratio of valid records over received (<= 1.0). ``None`` when no
        records were received.
    """

    received: int = 0
    valid: int = 0
    invalid: int = 0
    inserted: int = 0
    updated: int = 0
    duplicates: int = 0
    errors: int = 0
    quality_rate: float | None = None
    source: str | None = None
    resource: str | None = None
    ingestion_run_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "received": self.received,
            "valid": self.valid,
            "invalid": self.invalid,
            "inserted": self.inserted,
            "updated": self.updated,
            "duplicates": self.duplicates,
            "errors": self.errors,
            "quality_rate": self.quality_rate,
            "source": self.source,
            "resource": self.resource,
            "ingestion_run_id": self.ingestion_run_id,
            **self.extra,
        }


def quality_rate(valid: int, received: int) -> float | None:
    """Return the fraction of valid records over received (0..1).

    Returns ``None`` when ``received`` is 0 to avoid a division by zero.
    """
    if received <= 0:
        return None
    return round(valid / received, 6)


def metrics_from_etl(
    metrics: ETLMetrics,
    *,
    source: str | None = None,
    resource: str | None = None,
    ingestion_run_id: str | None = None,
) -> QualityMetrics:
    """Derive domain quality metrics from the coarse ETL counters.

    Mapping used by the quality reporter:

    * ``received = valid + invalid`` (the records that actually went through
      validation; raw records that failed to persist are out of scope here).
    * ``duplicates = unchanged`` (same natural key and payload hash).
    * ``new = inserted``, ``updated = updated``.
    * ``errors = invalid + failed``.
    """
    received = metrics.valid + metrics.invalid
    rate = quality_rate(metrics.valid, received)
    return QualityMetrics(
        received=received,
        valid=metrics.valid,
        invalid=metrics.invalid,
        inserted=metrics.inserted,
        updated=metrics.updated,
        duplicates=metrics.unchanged,
        errors=metrics.invalid + metrics.failed,
        quality_rate=rate,
        source=source,
        resource=resource,
        ingestion_run_id=ingestion_run_id,
        extra={
            "extracted": metrics.extracted,
            "raw_stored": metrics.raw_stored,
            "transformed": metrics.transformed,
            "failed": metrics.failed,
        },
    )
