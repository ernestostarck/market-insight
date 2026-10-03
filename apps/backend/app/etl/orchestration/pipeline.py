import logging
from dataclasses import dataclass
from typing import Any

from app.etl.error_handling.quarantine import (
    Quarantine,
    record_processing_error,
    record_validation_failure,
)
from app.etl.extraction.base import DataSource, ExtractionWindow
from app.etl.ingestion.raw_ingestor import RawIngestor
from app.etl.loading.base import RecordLoader
from app.etl.models import (
    ETLMetrics,
    ETLRunSummary,
    IngestionRunContext,
    StoredRawRecord,
)
from app.etl.quality.base import QualityReporter
from app.etl.transformation.base import RecordTransformer
from app.etl.validation.base import RecordValidator


def _record_batch_quality(
    pipeline: str, payloads: list[dict[str, Any]], invalid: int, duplicates: int
) -> None:
    """Publish the Data Quality Score for the batch; monitoring must never fail an ETL run."""
    if not payloads and not invalid:
        return
    try:
        from app.monitoring.data_quality import evaluate_batch

        evaluate_batch(pipeline, payloads, duplicates=duplicates, invalid_count=invalid)
    except Exception:
        logging.getLogger(__name__).warning("Could not record data quality for %s", pipeline, exc_info=True)


@dataclass(slots=True)
class ETLPipeline:
    source: DataSource
    raw_ingestor: RawIngestor
    validator: RecordValidator
    transformer: RecordTransformer
    loader: RecordLoader
    quality_reporter: QualityReporter | None = None
    quarantine: Quarantine | None = None

    async def run(
        self,
        run: IngestionRunContext,
        window: ExtractionWindow | None = None,
    ) -> ETLRunSummary:
        metrics = ETLMetrics()

        extracted = await self.source.extract(run=run, window=window)
        metrics.extracted = len(extracted)

        raw_stored = self.raw_ingestor.store(run=run, records=extracted)
        metrics.raw_stored = len(raw_stored)

        transformed = []
        quality_payloads: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        duplicates = 0
        quarantine_count = 0
        for raw_item in raw_stored:
            is_valid, transformed_item, normalized = self._validate_and_transform(raw_item, run)
            if not is_valid:
                metrics.invalid += 1
                quarantine_count += 1
                continue
            metrics.valid += 1
            transformed.append(transformed_item)
            quality_payloads.append(normalized)
            if raw_item.source_id in seen_ids:
                duplicates += 1
            seen_ids.add(raw_item.source_id)

        metrics.transformed = len(transformed)
        load_result = self.loader.load(run=run, records=transformed)
        metrics.inserted = load_result.inserted
        metrics.updated = load_result.updated
        metrics.unchanged = load_result.unchanged
        metrics.failed = load_result.failed

        if self.quality_reporter is not None:
            self.quality_reporter.emit(run=run, metrics=metrics)

        _record_batch_quality(run.resource, quality_payloads, metrics.invalid, duplicates)

        return ETLRunSummary(
            run=run,
            metrics=metrics,
            quarantine_count=quarantine_count,
        )

    def _validate_and_transform(
        self,
        raw_item: StoredRawRecord,
        run: IngestionRunContext,
    ) -> tuple[bool, object, dict[str, Any]]:
        result = self.validator.validate(raw_item)
        if not result.is_valid or result.normalized_payload is None:
            self._quarantine_validation_failure(raw_item, result, run)
            return False, None, {}

        try:
            transformed = self.transformer.transform(result.normalized_payload)
        except Exception as exc:
            self._quarantine_processing_error(raw_item, exc, run, "transform")
            return False, None, {}

        return True, transformed, dict(result.normalized_payload)

    def _quarantine_validation_failure(
        self,
        raw_item: StoredRawRecord,
        result: Any,
        run: IngestionRunContext,
    ) -> None:
        if self.quarantine is None:
            return
        record_validation_failure(
            self.quarantine,
            record=raw_item,
            result=result,
            ingestion_run_id=run.ingestion_run_id,
        )

    def _quarantine_processing_error(
        self,
        raw_item: StoredRawRecord,
        exc: BaseException,
        run: IngestionRunContext,
        stage: str,
    ) -> None:
        if self.quarantine is None:
            return
        record_processing_error(
            self.quarantine,
            error_type=f"{stage}_error",
            error_code=type(exc).__name__,
            message=str(exc),
            source=raw_item.source,
            resource=raw_item.resource,
            source_id=raw_item.source_id,
            payload=raw_item.payload,
            payload_hash=raw_item.payload_hash,
            exc=exc,
            ingestion_run_id=run.ingestion_run_id,
        )
