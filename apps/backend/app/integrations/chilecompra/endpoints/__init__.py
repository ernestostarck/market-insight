from app.integrations.chilecompra.endpoints.adjudicaciones import AdjudicacionesClient
from app.integrations.chilecompra.endpoints.contratos import ContratosClient
from app.integrations.chilecompra.endpoints.convenios_marco import ConveniosMarcoClient
from app.integrations.chilecompra.endpoints.empresas import EmpresasClient
from app.integrations.chilecompra.endpoints.licitaciones import LicitacionesClient
from app.integrations.chilecompra.endpoints.ordenes_compra import OrdenesCompraClient

__all__ = [
    "AdjudicacionesClient",
    "ConveniosMarcoClient",
    "ContratosClient",
    "EmpresasClient",
    "LicitacionesClient",
    "OrdenesCompraClient",
]
