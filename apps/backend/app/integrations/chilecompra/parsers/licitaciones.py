from __future__ import annotations

from datetime import datetime
from typing import Any

from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import (
    LicitacionAPIItem,
    LicitacionDetalleItem,
    LicitacionesAPIResponse,
    NormalizedLicitacion,
    NormalizedLicitacionDetalle,
)


def parse_licitaciones_payload(
    payload: dict[str, Any] | list[Any],
) -> LicitacionesAPIResponse:
    if isinstance(payload, list):
        payload = {"Cantidad": len(payload), "Listado": payload}
    if not isinstance(payload, dict):
        raise ChileCompraValidationError(
            "Licitaciones payload must be an object or list"
        )

    if (
        "Listado" in payload
        and "Cantidad" not in payload
        and isinstance(payload["Listado"], list)
    ):
        payload = {**payload, "Cantidad": len(payload["Listado"])}

    return LicitacionesAPIResponse.model_validate(payload)


def normalize_licitaciones(
    payload: dict[str, Any] | list[Any],
) -> list[NormalizedLicitacion]:
    parsed = parse_licitaciones_payload(payload)
    return [_normalize_licitacion(item) for item in parsed.listado]


def _normalize_licitacion(item: LicitacionAPIItem) -> NormalizedLicitacion:
    status_value = item.estado or str(item.codigo_estado or "UNKNOWN")
    return NormalizedLicitacion(
        external_id=item.codigo_externo,
        title=item.nombre or item.codigo_externo,
        status=status_value.strip().upper(),
        published_at=_parse_datetime(item.fecha_publicacion),
        closing_at=_parse_datetime(item.fecha_cierre),
        agency_code=item.codigo_organismo,
        agency_name=item.nombre_organismo,
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
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def parse_licitacion_detalle(payload: dict[str, Any]) -> NormalizedLicitacionDetalle | None:
    """Extract Descripcion/Comprador/Fechas/Items from a por_codigo detail
    response. Only the fields we actually use are modeled — the endpoint
    returns ~46 top-level keys, most irrelevant here."""
    listado = payload.get("Listado") if isinstance(payload, dict) else None
    if not listado:
        return None

    item = listado[0]
    comprador: dict[str, Any] = item.get("Comprador") or {}
    fechas: dict[str, Any] = item.get("Fechas") or {}
    items_block: dict[str, Any] = item.get("Items") or {}
    # Licitacion-level award metadata (date, offers count) — distinct from
    # each item's own nested Adjudicacion (proveedor/monto) below.
    adjudicacion_meta: dict[str, Any] = item.get("Adjudicacion") or {}

    items = []
    for raw in items_block.get("Listado") or []:
        item_award: dict[str, Any] = raw.get("Adjudicacion") or {}
        items.append(
            LicitacionDetalleItem(
                correlativo=raw.get("Correlativo"),
                codigo_producto=raw.get("CodigoProducto"),
                codigo_categoria=raw.get("CodigoCategoria"),
                categoria=raw.get("Categoria"),
                nombre_producto=raw.get("NombreProducto"),
                descripcion=raw.get("Descripcion"),
                unidad_medida=raw.get("UnidadMedida"),
                cantidad=raw.get("Cantidad"),
                proveedor_rut=item_award.get("RutProveedor"),
                proveedor_nombre=item_award.get("NombreProveedor"),
                monto_unitario=item_award.get("MontoUnitario"),
                cantidad_adjudicada=item_award.get("Cantidad"),
            )
        )

    return NormalizedLicitacionDetalle(
        external_id=item.get("CodigoExterno") or "",
        descripcion=item.get("Descripcion"),
        agency_code=comprador.get("CodigoOrganismo"),
        agency_name=comprador.get("NombreOrganismo"),
        agency_comuna=comprador.get("ComunaUnidad"),
        agency_region=comprador.get("RegionUnidad"),
        published_at=_parse_datetime(fechas.get("FechaPublicacion")),
        closing_at=_parse_datetime(fechas.get("FechaCierre")),
        monto_estimado=item.get("MontoEstimado"),
        fecha_adjudicacion=_parse_datetime(adjudicacion_meta.get("Fecha")),
        numero_oferentes=adjudicacion_meta.get("NumeroOferentes"),
        items=items,
    )
