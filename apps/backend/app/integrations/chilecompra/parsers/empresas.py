from __future__ import annotations

from datetime import datetime
from typing import Any

from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import (
    EmpresaAPIItem,
    EmpresasAPIResponse,
    NormalizedEmpresa,
)


def parse_empresas_payload(payload: dict[str, Any] | list[Any]) -> EmpresasAPIResponse:
    if isinstance(payload, list):
        payload = {"Cantidad": len(payload), "Listado": payload}
    if not isinstance(payload, dict):
        raise ChileCompraValidationError("Empresas payload must be an object or list")

    if (
        "Listado" in payload
        and "Cantidad" not in payload
        and isinstance(payload["Listado"], list)
    ):
        payload = {**payload, "Cantidad": len(payload["Listado"])}

    return EmpresasAPIResponse.model_validate(payload)


def normalize_empresas(payload: dict[str, Any] | list[Any]) -> list[NormalizedEmpresa]:
    parsed = parse_empresas_payload(payload)
    return [_normalize_empresa(item) for item in parsed.listado]


def _normalize_empresa(item: EmpresaAPIItem) -> NormalizedEmpresa:
    external_id = item.codigo_empresa or item.rut or ""
    if not external_id:
        raise ChileCompraValidationError("Empresa sin identificador externo")

    name = item.nombre_empresa or item.razon_social or external_id
    status = item.estado.strip().upper() if item.estado else None
    return NormalizedEmpresa(
        external_id=external_id,
        rut=item.rut,
        name=name,
        legal_name=item.razon_social,
        company_type=item.tipo_empresa,
        status=status,
        updated_at=_parse_datetime(item.fecha_actualizacion),
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
