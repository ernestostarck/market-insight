"""Read models for the analytics data marts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MarketMonthlyRead(AnalyticsReadModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "mes": "2026-01-01",
                "total_licitaciones": 128,
                "total_adjudicaciones": 94,
                "monto_total_adjudicado": "1250000000.00",
            }
        },
    )

    mes: date = Field(..., description="Calendar month (first day) this row summarizes.")
    total_licitaciones: int = Field(..., description="Tenders published in the month.")
    total_adjudicaciones: int = Field(..., description="Tenders awarded in the month.")
    monto_total_adjudicado: Decimal = Field(..., description="Total awarded amount, in CLP.")


class SupplierPerformanceRead(AnalyticsReadModel):
    razon_social: str = Field(..., description="Supplier's legal business name.")
    rut: str = Field(..., description="Supplier's RUT (Chilean tax ID).")
    total_adjudicaciones: int = Field(..., description="Total tenders awarded to this supplier.")
    monto_total_adjudicado: Decimal = Field(..., description="Total awarded amount, in CLP.")
    ratio_adjudicacion_promedio: Decimal | None = Field(
        None,
        description="Average award-to-estimate ratio across this supplier's awards; null when no award "
        "reports an estimated amount.",
    )
    ultima_adjudicacion: date | None = Field(
        None, description="Date of the supplier's most recent award; null when no award reports a date."
    )


class CategorySpendingRead(AnalyticsReadModel):
    categoria: str = Field(..., description="Product/service category name.")
    codigo_categoria: str = Field(..., description="Category code (rubro).")
    gasto_total_oc: Decimal = Field(..., description="Total spend via purchase orders in this category, in CLP.")
    numero_ordenes_compra: int = Field(..., description="Number of purchase orders in this category.")
    gasto_promedio_oc: Decimal = Field(..., description="Average purchase order amount in this category, in CLP.")


class DisabilityContractRead(AnalyticsReadModel):
    licitacion_id: str = Field(..., description="External tender identifier.")
    nombre: str = Field(..., description="Tender title.")
    descripcion: str = Field(..., description="Tender description.")
    monto_adjudicado: Decimal = Field(..., description="Awarded amount, in CLP.")
    proveedor: str = Field(..., description="Awarded supplier's name.")
    organismo: str = Field(..., description="Buying agency's name.")
    periodo: date = Field(..., description="Period (month) this award belongs to.")


class DataQualityMissingKeysRead(AnalyticsReadModel):
    fact_table: str = Field(..., description="Name of the fact table being checked.")
    missing_count: int = Field(..., description="Rows in fact_table missing an expected dimension key.")


class BidderRangeBucket(AnalyticsReadModel):
    rango_oferentes: str = Field(..., description="Human-readable bucket of bidder count.")
    total_procesos: int = Field(..., description="Awards falling in this bucket.")
    porcentaje: float = Field(..., description="Share of all awards with a known bidder count, in percent.")


class MarketObjectiveKpisRead(AnalyticsReadModel):
    licitaciones_relacionadas: int = Field(
        ..., description="Licitaciones matching the geriatría/discapacidad domain dictionary."
    )
    monto_total: float = Field(0, description="Sum of monto_adjudicado across those tenders' awards.")
    proveedores_activos: int = Field(0, description="Distinct suppliers awarded within this niche.")
    organismos_activos: int = Field(0, description="Distinct buying agencies publishing in this niche.")
    precio_promedio: float | None = Field(None, description="Average monto_adjudicado in this niche.")


class MarketObjectiveTrendPoint(AnalyticsReadModel):
    mes: date
    monto: float
    licitaciones: int


class MarketObjectiveLeader(AnalyticsReadModel):
    nombre: str
    rut: str | None = None
    monto_total: float
    porcentaje: float
    contratos: int


class MarketObjectiveCategoryShare(AnalyticsReadModel):
    codigo: str | None
    nombre: str | None
    monto: float
    porcentaje: float


class MarketObjectiveRead(AnalyticsReadModel):
    """Real "Mercado Objetivo: Discapacidad & Geriatría" summary.

    Scoped by matching each tender's own nombre/descripcion against the real,
    versioned domain dictionary (app/nlp/dictionary.py's 9 cross-cutting
    themes — geriatría, discapacidad, movilidad reducida, ayudas técnicas,
    etc.), not a pre-run NLP classification (only ~150 licitaciones have one
    so far, too sparse to drive this on its own).
    """

    kpis: MarketObjectiveKpisRead
    tasa_crecimiento: float | None = Field(
        None, description="Percent change in monto_adjudicado, latest vs. previous month in `tendencias`."
    )
    tendencias: list[MarketObjectiveTrendPoint]
    organismos_lideres: list[MarketObjectiveLeader]
    proveedores_lideres: list[MarketObjectiveLeader]
    categorias_relacionadas: list[MarketObjectiveCategoryShare]
    dictionary_terms_used: int = Field(
        ..., description="Real domain-dictionary surface forms used to match licitaciones."
    )


class PriceItemRead(AnalyticsReadModel):
    """One real `core.licitacion_item` row for price benchmarking — no brand/
    material/capacity fields exist in core.*, so unlike a fabricated product
    catalog, matching is by free-text search over nombre/descripcion (and
    optionally categoria_id) rather than fixed technical attributes."""

    licitacion_codigo: str | None
    organismo: str | None
    nombre: str | None
    descripcion: str | None
    precio_unitario: Decimal | None
    cantidad: Decimal | None
    unidad: str | None
    fecha: date | None
    categoria_codigo: str | None
    categoria_nombre: str | None


class CompetitionSummaryRead(AnalyticsReadModel):
    """Real competitive-intensity indicators from core.adjudicacion.

    `cantidad_ofertas` and `ratio_adjudicacion` are only populated when
    ChileCompra reports them for a given award, so these are averages over
    the awards that have them, not the full award universe.
    """

    oferentes_promedio: float | None = Field(
        None, description="Average number of bidders per award (core.adjudicacion.cantidad_ofertas)."
    )
    margen_descuento_promedio: float | None = Field(
        None, description="Average discount vs. estimated amount, in percent (1 - ratio_adjudicacion)."
    )
    total_adjudicaciones_con_oferentes: int = Field(
        0, description="Awards with a known bidder count, backing oferentes_promedio/distribucion."
    )
    distribucion_oferentes: list[BidderRangeBucket] = Field(default_factory=list)
