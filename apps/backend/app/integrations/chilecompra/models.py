from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LicitacionAPIItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    codigo_externo: str = Field(alias="CodigoExterno")
    nombre: str | None = Field(default=None, alias="Nombre")
    estado: str | None = Field(default=None, alias="Estado")
    codigo_estado: str | int | None = Field(default=None, alias="CodigoEstado")
    fecha_publicacion: str | None = Field(default=None, alias="FechaPublicacion")
    fecha_cierre: str | None = Field(default=None, alias="FechaCierre")
    codigo_organismo: str | None = Field(default=None, alias="CodigoOrganismo")
    nombre_organismo: str | None = Field(default=None, alias="NombreOrganismo")


class LicitacionesAPIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[LicitacionAPIItem] = Field(default_factory=list, alias="Listado")


class LicitacionDetalleItem(BaseModel):
    """One row of `Items.Listado[]` from the licitacion detail endpoint (por_codigo).

    The real award — winning proveedor and unit price — lives per item under
    its own nested `Adjudicacion` object, not in a separate `/adjudicaciones.json`
    resource (that endpoint only reports status changes, no proveedor/monto)."""

    correlativo: int | None = None
    codigo_producto: int | None = None
    codigo_categoria: str | None = None
    categoria: str | None = None
    nombre_producto: str | None = None
    descripcion: str | None = None
    unidad_medida: str | None = None
    cantidad: float | None = None
    proveedor_rut: str | None = None
    proveedor_nombre: str | None = None
    monto_unitario: float | None = None
    cantidad_adjudicada: float | None = None


class NormalizedLicitacionDetalle(BaseModel):
    """Detail-only fields (Descripcion, Comprador, Fechas, Items) that the
    listing endpoint never returns — only present via por_codigo."""

    external_id: str
    descripcion: str | None = None
    agency_code: str | None = None
    agency_name: str | None = None
    agency_comuna: str | None = None
    agency_region: str | None = None
    published_at: datetime | None = None
    closing_at: datetime | None = None
    monto_estimado: float | None = None
    fecha_adjudicacion: datetime | None = None
    numero_oferentes: int | None = None
    items: list[LicitacionDetalleItem] = Field(default_factory=list)


class NormalizedLicitacion(BaseModel):
    external_id: str
    title: str
    status: str
    published_at: datetime | None = None
    closing_at: datetime | None = None
    agency_code: str | None = None
    agency_name: str | None = None
    raw_payload: dict[str, Any]


class OrdenCompraAPIItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    codigo: str | None = Field(default=None, alias="Codigo")
    codigo_orden_compra: str | None = Field(default=None, alias="CodigoOrdenCompra")
    nombre: str | None = Field(default=None, alias="Nombre")
    estado: str | None = Field(default=None, alias="Estado")
    codigo_estado: str | int | None = Field(default=None, alias="CodigoEstado")
    fecha_creacion: str | None = Field(default=None, alias="FechaCreacion")
    fecha_emision: str | None = Field(default=None, alias="FechaEmision")
    codigo_proveedor: str | None = Field(default=None, alias="CodigoProveedor")
    nombre_proveedor: str | None = Field(default=None, alias="NombreProveedor")
    codigo_organismo: str | None = Field(default=None, alias="CodigoOrganismo")
    nombre_organismo: str | None = Field(default=None, alias="NombreOrganismo")
    monto_total: float | None = Field(default=None, alias="MontoTotal")


class OrdenesCompraAPIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[OrdenCompraAPIItem] = Field(default_factory=list, alias="Listado")


class NormalizedOrdenCompra(BaseModel):
    external_id: str
    title: str
    status: str
    created_at: datetime | None = None
    issued_at: datetime | None = None
    provider_code: str | None = None
    provider_name: str | None = None
    agency_code: str | None = None
    agency_name: str | None = None
    total_amount: float | None = None
    raw_payload: dict[str, Any]


class EmpresaAPIItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    codigo_empresa: str | None = Field(default=None, alias="CodigoEmpresa")
    rut: str | None = Field(default=None, alias="Rut")
    nombre_empresa: str | None = Field(default=None, alias="NombreEmpresa")
    razon_social: str | None = Field(default=None, alias="RazonSocial")
    tipo_empresa: str | None = Field(default=None, alias="TipoEmpresa")
    estado: str | None = Field(default=None, alias="Estado")
    fecha_actualizacion: str | None = Field(default=None, alias="FechaActualizacion")


class EmpresasAPIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[EmpresaAPIItem] = Field(default_factory=list, alias="Listado")


class NormalizedEmpresa(BaseModel):
    external_id: str
    rut: str | None = None
    name: str
    legal_name: str | None = None
    company_type: str | None = None
    status: str | None = None
    updated_at: datetime | None = None
    raw_payload: dict[str, Any]


class ContratoAPIItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    codigo: str | None = Field(default=None, alias="Codigo")
    codigo_contrato: str | None = Field(default=None, alias="CodigoContrato")
    codigo_externo: str | None = Field(default=None, alias="CodigoExterno")
    nombre: str | None = Field(default=None, alias="Nombre")
    estado: str | None = Field(default=None, alias="Estado")
    codigo_estado: str | int | None = Field(default=None, alias="CodigoEstado")
    fecha_creacion: str | None = Field(default=None, alias="FechaCreacion")
    fecha_inicio: str | None = Field(default=None, alias="FechaInicio")
    fecha_fin: str | None = Field(default=None, alias="FechaFin")
    codigo_proveedor: str | None = Field(default=None, alias="CodigoProveedor")
    nombre_proveedor: str | None = Field(default=None, alias="NombreProveedor")
    codigo_organismo: str | None = Field(default=None, alias="CodigoOrganismo")
    nombre_organismo: str | None = Field(default=None, alias="NombreOrganismo")
    monto_total: float | None = Field(default=None, alias="MontoTotal")


class ContratosAPIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[ContratoAPIItem] = Field(default_factory=list, alias="Listado")


class NormalizedContrato(BaseModel):
    external_id: str
    title: str
    status: str
    created_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    provider_code: str | None = None
    provider_name: str | None = None
    agency_code: str | None = None
    agency_name: str | None = None
    total_amount: float | None = None
    raw_payload: dict[str, Any]


class ConvenioMarcoAPIItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    codigo: str | None = Field(default=None, alias="Codigo")
    codigo_convenio: str | None = Field(default=None, alias="CodigoConvenio")
    codigo_externo: str | None = Field(default=None, alias="CodigoExterno")
    nombre: str | None = Field(default=None, alias="Nombre")
    estado: str | None = Field(default=None, alias="Estado")
    codigo_estado: str | int | None = Field(default=None, alias="CodigoEstado")
    fecha_creacion: str | None = Field(default=None, alias="FechaCreacion")
    fecha_inicio: str | None = Field(default=None, alias="FechaInicio")
    fecha_fin: str | None = Field(default=None, alias="FechaFin")
    codigo_organismo: str | None = Field(default=None, alias="CodigoOrganismo")
    nombre_organismo: str | None = Field(default=None, alias="NombreOrganismo")
    monto_total: float | None = Field(default=None, alias="MontoTotal")


class ConveniosMarcoAPIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[ConvenioMarcoAPIItem] = Field(default_factory=list, alias="Listado")


class NormalizedConvenioMarco(BaseModel):
    external_id: str
    title: str
    status: str
    created_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    agency_code: str | None = None
    agency_name: str | None = None
    total_amount: float | None = None
    raw_payload: dict[str, Any]


class AdjudicacionAPIItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    codigo: str | None = Field(default=None, alias="Codigo")
    codigo_adjudicacion: str | None = Field(default=None, alias="CodigoAdjudicacion")
    codigo_externo: str | None = Field(default=None, alias="CodigoExterno")
    nombre: str | None = Field(default=None, alias="Nombre")
    estado: str | None = Field(default=None, alias="Estado")
    codigo_estado: str | int | None = Field(default=None, alias="CodigoEstado")
    fecha_publicacion: str | None = Field(default=None, alias="FechaPublicacion")
    fecha_adjudicacion: str | None = Field(default=None, alias="FechaAdjudicacion")
    codigo_organismo: str | None = Field(default=None, alias="CodigoOrganismo")
    nombre_organismo: str | None = Field(default=None, alias="NombreOrganismo")
    codigo_proveedor: str | None = Field(default=None, alias="CodigoProveedor")
    nombre_proveedor: str | None = Field(default=None, alias="NombreProveedor")
    monto_adjudicado: float | str | None = Field(default=None, alias="MontoAdjudicado")
    monto_estimado: float | str | None = Field(default=None, alias="MontoEstimado")
    cantidad_ofertas: int | str | None = Field(default=None, alias="CantidadOfertas")


class AdjudicacionesAPIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[AdjudicacionAPIItem] = Field(default_factory=list, alias="Listado")
    fecha_creacion: str | None = Field(default=None, alias="FechaCreacion")
    version: str | None = Field(default=None, alias="Version")


class AdjudicacionesQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = None
    fecha: str | datetime | None = None
    estado: str | None = None
    codigo_organismo: str | None = None
    proveedor_rut: str | None = None
    page: int = 1
    page_size: int = 50

    @field_validator("codigo")
    @classmethod
    def _normalize_codigo(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    @field_validator("estado")
    @classmethod
    def _normalize_estado(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    @field_validator("codigo_organismo")
    @classmethod
    def _normalize_organismo(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("proveedor_rut")
    @classmethod
    def _normalize_rut(cls, value: str | None) -> str | None:
        if not value:
            return value
        return value.strip().replace(".", "").upper()

    @model_validator(mode="after")
    def _validate_bounds_and_filters(self) -> "AdjudicacionesQuery":
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= self.page_size <= 200:
            raise ValueError("page_size must be between 1 and 200")

        has_primary_filter = any(
            [self.codigo, self.fecha, self.estado, self.codigo_organismo]
        )
        if not has_primary_filter:
            raise ValueError(
                "At least one primary filter is required: codigo, fecha, estado, codigo_organismo"
            )
        return self


class NormalizedAdjudicacion(BaseModel):
    external_id: str
    title: str
    status: str
    published_at: datetime | None = None
    awarded_at: datetime | None = None
    agency_code: str | None = None
    agency_name: str | None = None
    provider_code: str | None = None
    provider_name: str | None = None
    awarded_amount: float | None = None
    estimated_amount: float | None = None
    award_ratio: float | None = None
    offers_count: int | None = None
    quality_flags: list[str] = Field(default_factory=list)
    raw_payload: dict[str, Any]


class AdjudicacionesScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ratio_outlier_upper: float = 1.5
    ratio_outlier_lower: float = 0.3
    amount_zscore_threshold: float = 2.5
    max_quality_flags_for_penalty: int = 4

    @model_validator(mode="after")
    def _validate_thresholds(self) -> "AdjudicacionesScoringConfig":
        if self.ratio_outlier_lower < 0:
            raise ValueError("ratio_outlier_lower must be >= 0")
        if self.ratio_outlier_upper <= self.ratio_outlier_lower:
            raise ValueError("ratio_outlier_upper must be > ratio_outlier_lower")
        if self.amount_zscore_threshold <= 0:
            raise ValueError("amount_zscore_threshold must be > 0")
        if self.max_quality_flags_for_penalty < 1:
            raise ValueError("max_quality_flags_for_penalty must be >= 1")
        return self


class AdjudicacionAnalyticInsight(BaseModel):
    external_id: str
    opportunity_score: float
    risk_level: str
    is_outlier: bool
    reasons: list[str] = Field(default_factory=list)
    award_ratio: float | None = None
    awarded_amount: float | None = None
    quality_flags: list[str] = Field(default_factory=list)


class AdjudicacionesAnalyticsSummary(BaseModel):
    total_items: int
    scored_items: int
    outlier_items: int
    avg_opportunity_score: float | None = None
    median_award_ratio: float | None = None
    risk_distribution: dict[str, int] = Field(default_factory=dict)


class AdjudicacionesAnalyticsResult(BaseModel):
    summary: AdjudicacionesAnalyticsSummary
    items: list[AdjudicacionAnalyticInsight] = Field(default_factory=list)
