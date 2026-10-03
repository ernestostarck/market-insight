from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.etl.extraction.base import DataSource, ExtractionWindow
from app.etl.extraction.checkpoints import (
    CheckpointStore,
    ExtractionCheckpoint,
    utcnow,
)
from app.etl.models import IngestionRunContext, RawRecord
from app.integrations.chilecompra.sdk import ChileCompraClient


class ChileCompraAPIDataSource(DataSource):
    """Extracts raw licitaciones payloads from ChileCompra API."""

    source_name = "chilecompra_api"

    def __init__(
        self,
        client: ChileCompraClient,
        *,
        resource: str = "licitaciones",
        checkpoint_store: CheckpointStore | None = None,
    ) -> None:
        self._client = client
        self._resource = resource
        self._checkpoints = checkpoint_store

    async def extract(
        self,
        run: IngestionRunContext,
        window: ExtractionWindow | None = None,
    ) -> list[RawRecord]:
        start_date, end_date = self._resolve_window(window)

        records: list[RawRecord] = []
        current_date = start_date
        while current_date <= end_date:
            response = await self._client.licitaciones.por_fecha(
                current_date.strftime("%d%m%Y")
            )
            items = _extract_items(response)
            extracted_at = datetime.now(timezone.utc)
            for index, item in enumerate(items):
                source_id = _resolve_source_id(item, fallback_index=index)
                records.append(
                    RawRecord(
                        source=self.source_name,
                        resource=self._resource,
                        source_id=source_id,
                        payload=item,
                        extracted_at=extracted_at,
                        metadata={"snapshot_date": current_date.isoformat()},
                    )
                )
            current_date = current_date + timedelta(days=1)

        self._update_checkpoint(end_date)
        return records

    def _resolve_window(self, window: ExtractionWindow | None) -> tuple[date, date]:
        if window and window.start_at is not None:
            start_date = window.start_at.date()
        else:
            checkpoint_date = self._checkpoint_date()
            start_date = (
                checkpoint_date + timedelta(days=1)
                if checkpoint_date is not None
                else utcnow().date()
            )

        if window and window.end_at is not None:
            end_date = window.end_at.date()
        else:
            end_date = start_date

        if end_date < start_date:
            raise ValueError("extraction window end_at must be >= start_at")
        return start_date, end_date

    def _checkpoint_date(self) -> date | None:
        if self._checkpoints is None:
            return None
        checkpoint = self._checkpoints.get(
            source=self.source_name,
            resource=self._resource,
        )
        if checkpoint is None:
            return None
        try:
            return date.fromisoformat(checkpoint.marker)
        except ValueError as exc:
            raise ValueError(
                f"invalid checkpoint marker for {self.source_name}/{self._resource}: {checkpoint.marker}"
            ) from exc

    def _update_checkpoint(self, checkpoint_date: date) -> None:
        if self._checkpoints is None:
            return
        self._checkpoints.set(
            ExtractionCheckpoint(
                source=self.source_name,
                resource=self._resource,
                marker=checkpoint_date.isoformat(),
                updated_at=utcnow(),
            )
        )


def _extract_items(response: Any) -> list[dict[str, Any]]:
    if hasattr(response, "listado"):
        items = getattr(response, "listado")
    elif isinstance(response, dict):
        items = response.get("Listado", [])
    else:
        items = []

    normalized: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return normalized

    for item in items:
        if hasattr(item, "model_dump"):
            normalized.append(item.model_dump(by_alias=True, exclude_none=False))
        elif isinstance(item, dict):
            normalized.append(item)
    return normalized


def _resolve_source_id(item: dict[str, Any], fallback_index: int) -> str:
    for key in ("CodigoExterno", "Codigo", "CodigoLicitacion"):
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return f"unknown-{fallback_index}"
