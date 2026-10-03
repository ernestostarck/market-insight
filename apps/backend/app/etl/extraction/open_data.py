from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.etl.extraction.base import DataSource, ExtractionWindow
from app.etl.extraction.checkpoints import (
    CheckpointStore,
    ExtractionCheckpoint,
    utcnow,
)
from app.etl.models import IngestionRunContext, RawRecord


class OpenDataDataSource(DataSource):
    """Bulk extractor for historical datasets from local JSONL/NDJSON files."""

    source_name = "open_data"

    def __init__(
        self,
        dataset_path: str | Path,
        *,
        resource: str,
        source_id_field: str,
        checkpoint_store: CheckpointStore | None = None,
    ) -> None:
        self._path = Path(dataset_path)
        self._resource = resource
        self._source_id_field = source_id_field
        self._checkpoints = checkpoint_store

    async def extract(
        self,
        run: IngestionRunContext,
        window: ExtractionWindow | None = None,
    ) -> list[RawRecord]:
        _ = window
        batch_size = _batch_size_from_params(run.params)
        start_offset = self._checkpoint_offset()

        records: list[RawRecord] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for index, line in enumerate(fh):
                if index < start_offset:
                    continue
                if batch_size is not None and len(records) >= batch_size:
                    break

                payload = json.loads(line)
                source_id = _resolve_source_id(
                    payload,
                    source_id_field=self._source_id_field,
                    line_number=index,
                )
                records.append(
                    RawRecord(
                        source=self.source_name,
                        resource=self._resource,
                        source_id=source_id,
                        payload=payload,
                        extracted_at=utcnow(),
                        metadata={"line_number": str(index)},
                    )
                )

        next_offset = start_offset + len(records)
        self._update_checkpoint(next_offset)
        return records

    def _checkpoint_offset(self) -> int:
        if self._checkpoints is None:
            return 0
        checkpoint = self._checkpoints.get(
            source=self.source_name,
            resource=self._resource,
        )
        if checkpoint is None:
            return 0
        return int(checkpoint.marker)

    def _update_checkpoint(self, next_offset: int) -> None:
        if self._checkpoints is None:
            return
        self._checkpoints.set(
            ExtractionCheckpoint(
                source=self.source_name,
                resource=self._resource,
                marker=str(next_offset),
                updated_at=utcnow(),
            )
        )


def _batch_size_from_params(params: dict[str, str]) -> int | None:
    raw = params.get("batch_size")
    if raw is None:
        return None
    value = int(raw)
    if value < 1:
        raise ValueError("batch_size must be greater than or equal to 1")
    return value


def _resolve_source_id(
    payload: dict[str, Any],
    *,
    source_id_field: str,
    line_number: int,
) -> str:
    value = payload.get(source_id_field)
    if value is None or not str(value).strip():
        return f"line-{line_number}"
    return str(value)
