from __future__ import annotations

from datetime import datetime
from typing import Any

from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import (
    NormalizedOrdenCompra,
    OrdenCompraAPIItem,
    OrdenesCompraAPIResponse,
)


def parse_ordenes_compra_payload(
    payload: dict[str, Any] | list[Any],
) -> OrdenesCompraAPIResponse:
    if isinstance(payload, list):
        payload = {"Cantidad": len(payload), "Listado": payload}
    if not isinstance(payload, dict):
        raise ChileCompraValidationError(
            "Ordenes de compra payload must be an object or list"
        )

    if (
        "Listado" in payload
        and "Cantidad" not in payload
        and isinstance(payload["Listado"], list)
    ):
        payload = {**payload, "Cantidad": len(payload["Listado"])}

    return OrdenesCompraAPIResponse.model_validate(payload)


def normalize_ordenes_compra(
    payload: dict[str, Any] | list[Any],
) -> list[NormalizedOrdenCompra]:
    parsed = parse_ordenes_compra_payload(payload)
    return [_normalize_orden_compra(item) for item in parsed.listado]


def _normalize_orden_compra(item: OrdenCompraAPIItem) -> NormalizedOrdenCompra:
    external_id = item.codigo_orden_compra or item.codigo or ""
    if not external_id:
        raise ChileCompraValidationError("Orden de compra sin codigo externo")

    status_value = item.estado or str(item.codigo_estado or "UNKNOWN")
    return NormalizedOrdenCompra(
        external_id=external_id,
        title=item.nombre or external_id,
        status=status_value.strip().upper(),
        created_at=_parse_datetime(item.fecha_creacion),
        issued_at=_parse_datetime(item.fecha_emision),
        provider_code=item.codigo_proveedor,
        provider_name=item.nombre_proveedor,
        agency_code=item.codigo_organismo,
        agency_name=item.nombre_organismo,
        total_amount=item.monto_total,
        raw_payload=item.model_dump(by_alias=True),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    candidate = value.strip()
    for fmt in (
        "%d%m%Y",
        "%Y%m%d",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None
