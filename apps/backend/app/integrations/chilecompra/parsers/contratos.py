from __future__ import annotations

from datetime import datetime
from typing import Any

from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import (
    ContratoAPIItem,
    ContratosAPIResponse,
    NormalizedContrato,
)


def parse_contratos_payload(
    payload: dict[str, Any] | list[Any],
) -> ContratosAPIResponse:
    if isinstance(payload, list):
        payload = {"Cantidad": len(payload), "Listado": payload}
    if not isinstance(payload, dict):
        raise ChileCompraValidationError("Contratos payload must be an object or list")

    if (
        "Listado" in payload
        and "Cantidad" not in payload
        and isinstance(payload["Listado"], list)
    ):
        payload = {**payload, "Cantidad": len(payload["Listado"])}

    return ContratosAPIResponse.model_validate(payload)


def normalize_contratos(
    payload: dict[str, Any] | list[Any],
) -> list[NormalizedContrato]:
    parsed = parse_contratos_payload(payload)
    return [_normalize_contrato(item) for item in parsed.listado]


def _normalize_contrato(item: ContratoAPIItem) -> NormalizedContrato:
    external_id = item.codigo_contrato or item.codigo or item.codigo_externo or ""
    if not external_id:
        raise ChileCompraValidationError("Contrato sin codigo externo")

    status_value = item.estado or str(item.codigo_estado or "UNKNOWN")
    return NormalizedContrato(
        external_id=external_id,
        title=item.nombre or external_id,
        status=status_value.strip().upper(),
        created_at=_parse_datetime(item.fecha_creacion),
        start_at=_parse_datetime(item.fecha_inicio),
        end_at=_parse_datetime(item.fecha_fin),
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
