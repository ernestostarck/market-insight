"""On-demand licitacion detail enrichment: Items, Descripcion, full Organismo.

The daily bulk sync (app/etl/orchestration/jobs.py) only calls ChileCompra's
listing endpoint (~1000+ licitaciones/day, 4 shallow fields each). Items,
Descripcion and full Comprador/Fechas data only exist behind the detail
endpoint (por_codigo) — calling it for every listed licitacion would multiply
the daily API volume by 1000x, so this is invoked one licitacion at a time,
on demand (e.g. before building a 6.2 TenderDocument), not from the beat
schedule. See docs/07-ai/document-processing.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from sqlalchemy.engine import Connection

from app.etl.loading.core_schema import (
    CoreAdjudicacionLoader,
    CoreLicitacionItemLoader,
    CoreLicitacionLoader,
)
from app.etl.models import IngestionRunContext, TransformedRecord
from app.etl.transformation.hashing import payload_hash
from app.etl.transformation.keys import natural_key
from app.integrations.chilecompra.parsers.licitaciones import parse_licitacion_detalle


class _LicitacionesResource(Protocol):
    async def detalle_raw(self, codigo: str) -> dict: ...


class _ChileCompraClientLike(Protocol):
    licitaciones: _LicitacionesResource


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    codigo: str
    found: bool
    items_upserted: int
    adjudicaciones_upserted: int = 0


async def enrich_licitacion_detail(
    codigo: str,
    *,
    client: _ChileCompraClientLike,
    licitacion_loader: CoreLicitacionLoader,
    item_loader: CoreLicitacionItemLoader,
    connection_factory: Callable[[], Connection],
    adjudicacion_loader: CoreAdjudicacionLoader | None = None,
) -> EnrichmentResult:
    raw = await client.licitaciones.detalle_raw(codigo)
    detail = parse_licitacion_detalle(raw)
    if detail is None:
        return EnrichmentResult(codigo=codigo, found=False, items_upserted=0)

    # Reuses CoreLicitacionLoader.load()'s upsert/dedupe path (same one the
    # daily sync uses) via a synthetic TransformedRecord, instead of
    # duplicating the organismo-resolution/upsert logic here.
    payload = {
        key: value
        for key, value in {
            "descripcion": detail.descripcion,
            "agency_code": detail.agency_code,
            "agency_name": detail.agency_name,
            "fecha_publicacion": detail.published_at.isoformat() if detail.published_at else None,
            "fecha_cierre": detail.closing_at.isoformat() if detail.closing_at else None,
        }.items()
        if value is not None
    }
    record = TransformedRecord(
        entity="licitacion",
        natural_key=natural_key("licitacion", detail.external_id),
        payload=payload,
        source_id=detail.external_id,
        payload_hash=payload_hash(payload),
    )
    licitacion_loader.load(_enrichment_run_context(codigo), [record])

    connection = connection_factory()
    try:
        items_upserted = item_loader.upsert_items(
            connection, licitacion_codigo=detail.external_id, items=detail.items,
        )
        adjudicaciones_upserted = 0
        if adjudicacion_loader is not None:
            adjudicaciones_upserted = adjudicacion_loader.upsert_from_items(
                connection,
                licitacion_codigo=detail.external_id,
                monto_estimado=detail.monto_estimado,
                fecha_adjudicacion=detail.fecha_adjudicacion,
                numero_oferentes=detail.numero_oferentes,
                items=detail.items,
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return EnrichmentResult(
        codigo=codigo,
        found=True,
        items_upserted=items_upserted,
        adjudicaciones_upserted=adjudicaciones_upserted,
    )


def _enrichment_run_context(codigo: str) -> IngestionRunContext:
    """Synthetic run context — enrichment runs outside ETLPipeline/IncrementalETL
    (one licitacion at a time, not a windowed extraction run), but
    CoreLicitacionLoader.load() still needs one for logging/error context."""
    stamp = datetime.now(timezone.utc)
    return IngestionRunContext(
        ingestion_run_id=f"enrich-{codigo}-{stamp.strftime('%Y%m%d-%H%M%S')}",
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="enrichment-1",
        started_at=stamp,
    )
