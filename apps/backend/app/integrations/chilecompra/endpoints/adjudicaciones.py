from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

from pydantic import ValidationError

from app.integrations.chilecompra.client import ChileCompraHTTPClient
from app.integrations.chilecompra.exceptions import (
    ChileCompraNotFoundError,
    ChileCompraValidationError,
)
from app.integrations.chilecompra.models import (
    AdjudicacionesAnalyticsResult,
    AdjudicacionesAPIResponse,
    AdjudicacionesQuery,
    AdjudicacionesScoringConfig,
    NormalizedAdjudicacion,
)
from app.integrations.chilecompra.parsers.adjudicaciones import (
    analyze_adjudicaciones,
    normalize_adjudicaciones,
    parse_adjudicaciones_payload,
)

_CODIGO_PATTERN = re.compile(r"^\d+-[A-Za-z0-9-]+$")
_ESTADO_PATTERN = re.compile(r"^[A-Za-z_\-\s]+$")
_RUT_PATTERN = re.compile(r"^\d{7,8}-[0-9K]$")


class AdjudicacionesClient:
    """Resource client for adjudicaciones endpoints with advanced query support."""

    _PATH = "/adjudicaciones.json"
    _FALLBACK_PATH = "/licitaciones.json"
    _FALLBACK_SOURCE_RESOURCE = "licitaciones.json"

    def __init__(self, http_client: ChileCompraHTTPClient) -> None:
        self._http = http_client

    async def por_codigo(self, codigo: str) -> AdjudicacionesAPIResponse:
        normalized_codigo = _normalize_codigo(codigo)
        return await self._fetch(params={"codigo": normalized_codigo})

    async def por_fecha(
        self, fecha: str | date | datetime
    ) -> AdjudicacionesAPIResponse:
        normalized_fecha = _normalize_fecha(fecha)
        return await self._fetch(params={"fecha": normalized_fecha})

    async def por_estado(self, estado: str) -> AdjudicacionesAPIResponse:
        normalized_estado = _normalize_estado(estado)
        return await self._fetch(params={"estado": normalized_estado})

    async def diarias(self) -> AdjudicacionesAPIResponse:
        return await self._fetch()

    async def buscar_avanzado(
        self, query: AdjudicacionesQuery | dict[str, Any]
    ) -> AdjudicacionesAPIResponse:
        query_model = _ensure_query(query)
        params = _build_query_params(query_model)
        return await self._fetch(params=params)

    async def normalizadas_por_fecha(
        self, fecha: str | date | datetime
    ) -> list[NormalizedAdjudicacion]:
        normalized_fecha = _normalize_fecha(fecha)
        payload = await self._get_json_with_fallback(params={"fecha": normalized_fecha})
        return normalize_adjudicaciones(payload)

    async def normalizadas_busqueda_avanzada(
        self, query: AdjudicacionesQuery | dict[str, Any]
    ) -> list[NormalizedAdjudicacion]:
        query_model = _ensure_query(query)
        params = _build_query_params(query_model)
        payload = await self._get_json_with_fallback(params=params)
        return normalize_adjudicaciones(payload)

    async def analisis_oportunidad_por_fecha(
        self,
        fecha: str | date | datetime,
        config: AdjudicacionesScoringConfig | None = None,
    ) -> AdjudicacionesAnalyticsResult:
        normalized_fecha = _normalize_fecha(fecha)
        payload = await self._get_json_with_fallback(params={"fecha": normalized_fecha})
        return analyze_adjudicaciones(payload, config=config)

    async def analisis_oportunidad_busqueda_avanzada(
        self,
        query: AdjudicacionesQuery | dict[str, Any],
        config: AdjudicacionesScoringConfig | None = None,
    ) -> AdjudicacionesAnalyticsResult:
        query_model = _ensure_query(query)
        params = _build_query_params(query_model)
        payload = await self._get_json_with_fallback(params=params)
        return analyze_adjudicaciones(payload, config=config)

    async def _fetch(
        self, params: dict[str, str] | None = None
    ) -> AdjudicacionesAPIResponse:
        payload = await self._get_json_with_fallback(params=params)
        return parse_adjudicaciones_payload(payload)

    async def _get_json_with_fallback(
        self, params: dict[str, str] | None = None
    ) -> dict[str, Any] | list[Any]:
        try:
            return await self._http.get_json(self._PATH, params=params)
        except ChileCompraNotFoundError:
            payload = await self._http.get_json(self._FALLBACK_PATH, params=params)
            return _annotate_fallback_payload(
                payload,
                source_resource=self._FALLBACK_SOURCE_RESOURCE,
            )


def _annotate_fallback_payload(
    payload: dict[str, Any] | list[Any],
    *,
    source_resource: str,
) -> dict[str, Any] | list[Any]:
    if isinstance(payload, list):
        annotated_items = [
            {**item, "__source_resource": source_resource}
            if isinstance(item, dict)
            else item
            for item in payload
        ]
        return annotated_items

    if not isinstance(payload, dict):
        return payload

    annotated = {**payload, "__source_resource": source_resource}
    listado = payload.get("Listado")
    if isinstance(listado, list):
        annotated["Listado"] = [
            {**item, "__source_resource": source_resource}
            if isinstance(item, dict)
            else item
            for item in listado
        ]
    return annotated


def _ensure_query(query: AdjudicacionesQuery | dict[str, Any]) -> AdjudicacionesQuery:
    if isinstance(query, AdjudicacionesQuery):
        model = query
    else:
        try:
            model = AdjudicacionesQuery.model_validate(query)
        except ValidationError as exc:
            raise ChileCompraValidationError(
                "Parametros de busqueda avanzada invalidos"
            ) from exc

    if model.codigo and not _CODIGO_PATTERN.match(model.codigo):
        raise ChileCompraValidationError(
            "Codigo de adjudicacion invalido. Formato esperado: 1234-56-LP23"
        )

    if model.estado and not _ESTADO_PATTERN.match(model.estado):
        raise ChileCompraValidationError("Estado de adjudicacion invalido")

    if model.proveedor_rut and not _RUT_PATTERN.match(model.proveedor_rut):
        raise ChileCompraValidationError("RUT de proveedor invalido")

    return model


def _build_query_params(query: AdjudicacionesQuery) -> dict[str, str]:
    params: dict[str, str] = {
        "page": str(query.page),
        "page_size": str(query.page_size),
    }
    if query.codigo:
        params["codigo"] = query.codigo
    if query.fecha:
        params["fecha"] = _normalize_fecha(query.fecha)
    if query.estado:
        params["estado"] = query.estado
    if query.codigo_organismo:
        params["codigoOrganismo"] = query.codigo_organismo
    if query.proveedor_rut:
        params["proveedorRut"] = query.proveedor_rut
    return params


def _normalize_codigo(codigo: str) -> str:
    value = codigo.strip().upper()
    if not value or not _CODIGO_PATTERN.match(value):
        raise ChileCompraValidationError(
            "Codigo de adjudicacion invalido. Formato esperado: 1234-56-LP23"
        )
    return value


def _normalize_fecha(fecha: str | date | datetime) -> str:
    if isinstance(fecha, datetime):
        return fecha.strftime("%d%m%Y")
    if isinstance(fecha, date):
        return fecha.strftime("%d%m%Y")

    raw = fecha.strip()
    if not raw:
        raise ChileCompraValidationError("Fecha de adjudicacion vacia")

    if raw.isdigit() and len(raw) == 8:
        try:
            parsed = datetime.strptime(raw, "%d%m%Y").replace(tzinfo=UTC)
            return parsed.strftime("%d%m%Y")
        except ValueError:
            try:
                parsed = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=UTC)
                return parsed.strftime("%d%m%Y")
            except ValueError as exc:
                raise ChileCompraValidationError(
                    "Fecha invalida. Use DDMMYYYY o YYYYMMDD"
                ) from exc

    raise ChileCompraValidationError("Fecha invalida. Use DDMMYYYY o YYYYMMDD")


def _normalize_estado(estado: str) -> str:
    value = estado.strip().upper()
    if not value or not _ESTADO_PATTERN.match(value):
        raise ChileCompraValidationError("Estado de adjudicacion invalido")
    return value
