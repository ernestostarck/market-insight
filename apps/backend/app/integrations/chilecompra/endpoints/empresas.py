from __future__ import annotations

import re

from app.integrations.chilecompra.client import ChileCompraHTTPClient
from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import EmpresasAPIResponse, NormalizedEmpresa
from app.integrations.chilecompra.parsers.empresas import (
    normalize_empresas,
    parse_empresas_payload,
)

_RUT_PATTERN = re.compile(r"^\d{7,8}-[0-9K]$")


class EmpresasClient:
    """Resource client for empresas/proveedores endpoints."""

    _PATH = "/empresas.json"

    def __init__(self, http_client: ChileCompraHTTPClient) -> None:
        self._http = http_client

    async def buscar_proveedor(self, rut: str) -> EmpresasAPIResponse:
        normalized_rut = _normalize_rut(rut)
        return await self._fetch(params={"rut": normalized_rut})

    async def buscar_compradores(self) -> EmpresasAPIResponse:
        return await self.buscar_por_tipo("compradores")

    async def buscar_por_tipo(self, tipo: str) -> EmpresasAPIResponse:
        normalized_tipo = _normalize_tipo(tipo)
        return await self._fetch(params={"tipo": normalized_tipo})

    async def normalizadas_por_rut(self, rut: str) -> list[NormalizedEmpresa]:
        normalized_rut = _normalize_rut(rut)
        payload = await self._http.get_json(self._PATH, params={"rut": normalized_rut})
        return normalize_empresas(payload)

    async def _fetch(self, params: dict[str, str]) -> EmpresasAPIResponse:
        payload = await self._http.get_json(self._PATH, params=params)
        return parse_empresas_payload(payload)


def _normalize_rut(rut: str) -> str:
    value = rut.strip().replace(".", "").upper()
    if not _RUT_PATTERN.match(value):
        raise ChileCompraValidationError("RUT invalido. Formato esperado: 12345678-9")
    return value


def _normalize_tipo(tipo: str) -> str:
    value = tipo.strip().lower()
    allowed = {"compradores", "proveedores", "vendedores"}
    if value not in allowed:
        raise ChileCompraValidationError(
            "Tipo de empresa invalido. Valores permitidos: compradores, proveedores, vendedores"
        )
    return value
