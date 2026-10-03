from __future__ import annotations

import re
from datetime import date, datetime

from app.integrations.chilecompra.client import ChileCompraHTTPClient
from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import (
    ConveniosMarcoAPIResponse,
    NormalizedConvenioMarco,
)
from app.integrations.chilecompra.parsers.convenios_marco import (
    normalize_convenios_marco,
    parse_convenios_marco_payload,
)

_CODIGO_PATTERN = re.compile(r"^\d+-[A-Za-z0-9-]+$")
_ESTADO_PATTERN = re.compile(r"^[A-Za-z_\-\s]+$")


class ConveniosMarcoClient:
    """Resource client for convenios marco endpoints."""

    _PATH = "/conveniomarco.json"

    def __init__(self, http_client: ChileCompraHTTPClient) -> None:
        self._http = http_client

    async def por_codigo(self, codigo: str) -> ConveniosMarcoAPIResponse:
        normalized_codigo = _normalize_codigo(codigo)
        return await self._fetch(params={"codigo": normalized_codigo})

    async def por_fecha(
        self, fecha: str | date | datetime
    ) -> ConveniosMarcoAPIResponse:
        normalized_fecha = _normalize_fecha(fecha)
        return await self._fetch(params={"fecha": normalized_fecha})

    async def por_estado(self, estado: str) -> ConveniosMarcoAPIResponse:
        normalized_estado = _normalize_estado(estado)
        return await self._fetch(params={"estado": normalized_estado})

    async def diarias(self) -> ConveniosMarcoAPIResponse:
        return await self._fetch()

    async def normalizados_por_fecha(
        self, fecha: str | date | datetime
    ) -> list[NormalizedConvenioMarco]:
        normalized_fecha = _normalize_fecha(fecha)
        payload = await self._http.get_json(
            self._PATH, params={"fecha": normalized_fecha}
        )
        return normalize_convenios_marco(payload)

    async def _fetch(
        self, params: dict[str, str] | None = None
    ) -> ConveniosMarcoAPIResponse:
        payload = await self._http.get_json(self._PATH, params=params)
        return parse_convenios_marco_payload(payload)


def _normalize_codigo(codigo: str) -> str:
    value = codigo.strip().upper()
    if not value or not _CODIGO_PATTERN.match(value):
        raise ChileCompraValidationError(
            "Codigo de convenio marco invalido. Formato esperado: 1234-56-LP23"
        )
    return value


def _normalize_fecha(fecha: str | date | datetime) -> str:
    if isinstance(fecha, datetime):
        return fecha.strftime("%d%m%Y")
    if isinstance(fecha, date):
        return fecha.strftime("%d%m%Y")

    raw = fecha.strip()
    if not raw:
        raise ChileCompraValidationError("Fecha de convenio marco vacia")

    if raw.isdigit() and len(raw) == 8:
        try:
            parsed = datetime.strptime(raw, "%d%m%Y")
            return parsed.strftime("%d%m%Y")
        except ValueError:
            try:
                parsed = datetime.strptime(raw, "%Y%m%d")
                return parsed.strftime("%d%m%Y")
            except ValueError as exc:
                raise ChileCompraValidationError(
                    "Fecha invalida. Use DDMMYYYY o YYYYMMDD"
                ) from exc

    raise ChileCompraValidationError("Fecha invalida. Use DDMMYYYY o YYYYMMDD")


def _normalize_estado(estado: str) -> str:
    value = estado.strip().upper()
    if not value or not _ESTADO_PATTERN.match(value):
        raise ChileCompraValidationError("Estado de convenio marco invalido")
    return value
