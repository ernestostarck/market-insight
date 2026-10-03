from __future__ import annotations

from app.integrations.chilecompra.client import ChileCompraHTTPClient
from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.endpoints import (
    AdjudicacionesClient,
    ContratosClient,
    ConveniosMarcoClient,
    EmpresasClient,
    LicitacionesClient,
    OrdenesCompraClient,
)


class ChileCompraClient:
    """SDK facade exposing ChileCompra resources through a single entrypoint."""

    def __init__(self, http_client: ChileCompraHTTPClient) -> None:
        self._http = http_client
        self.licitaciones = LicitacionesClient(http_client)
        self.ordenes_compra = OrdenesCompraClient(http_client)
        self.empresas = EmpresasClient(http_client)
        self.contratos = ContratosClient(http_client)
        self.convenios_marco = ConveniosMarcoClient(http_client)
        self.adjudicaciones = AdjudicacionesClient(http_client)

    @classmethod
    def from_config(cls, config: ChileCompraConfig) -> "ChileCompraClient":
        return cls(ChileCompraHTTPClient(config))

    @classmethod
    def from_settings(cls) -> "ChileCompraClient":
        config = ChileCompraConfig.from_settings()
        return cls.from_config(config)
