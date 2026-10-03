from app.models.adjudicacion_analytics_snapshot import AdjudicacionAnalyticsSnapshot
from app.models.comprador import Comprador
from app.models.contrato import Contrato
from app.models.core import (
    Adjudicacion,
    Categoria,
    Documento,
    Licitacion,
    LicitacionItem,
    Oferta,
    OrdenCompra,
    OrdenCompraItem,
    Organismo,
    Producto,
    Proveedor,
)
from app.models.document_metadata import DocumentMetadata
from app.models.dw import (
    DimCategoria,
    DimEstadoLicitacion,
    DimFecha,
    DimOrganismo,
    DimProducto,
    DimProveedor,
    DimTipoLicitacion,
    DimUbicacion,
    FactAdjudicacion,
    FactLicitacion,
    FactOferta,
    FactOrdenCompra,
)
from app.models.marts import (
    CategorySpending,
    DisabilityContract,
    DQMissingKeys,
    LineageMartToDW,
    MarketMonthly,
    SupplierPerformance,
)
from app.models.ai import Conversation, Message
from app.models.etl_run import ETLRun
from app.models.raw_ingestion_event import RawIngestionEvent
from app.models.user import SecurityAuditLog, User, UserSession
from app.models.knowledge import (
    Category, Chunk, Classification, Concept, DatasetVersion, Document, Embedding, Entity,
    GoldLabel, HumanReview, Keyword, ModelVersion, Product, ProductConcept, Relationship, Rule, Subcategory,
)

__all__ = [
    "Conversation",
    "Message",

    "AdjudicacionAnalyticsSnapshot",
    "DocumentMetadata",
    "ETLRun",
    "RawIngestionEvent",
    "User",
    "Category",
    "Chunk",
    "Classification",
    "Concept",
    "DatasetVersion",
    "Document",
    "Embedding",
    "Entity",
    "GoldLabel",
    "HumanReview",
    "Keyword",
    "ModelVersion",
    "Product",
    "ProductConcept",
    "Relationship",
    "Rule",
    "Subcategory",
    # Core canonical model
    "Organismo",
    "Proveedor",
    "Licitacion",
    "LicitacionItem",
    "Oferta",
    "Adjudicacion",
    "OrdenCompra",
    "OrdenCompraItem",
    "Categoria",
    "Producto",
    "Documento",
    "Comprador",
    "Contrato",
    # Dimensional model (dw)
    "DimFecha",
    "DimOrganismo",
    "DimProveedor",
    "DimCategoria",
    "DimProducto",
    "DimUbicacion",
    "DimEstadoLicitacion",
    "DimTipoLicitacion",
    "FactLicitacion",
    "FactOferta",
    "FactAdjudicacion",
    "FactOrdenCompra",
    # Data marts
    "MarketMonthly",
    "SupplierPerformance",
    "CategorySpending",
    "DisabilityContract",
    "DQMissingKeys",
    "LineageMartToDW",
]
