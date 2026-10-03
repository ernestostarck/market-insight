from datetime import datetime

from pydantic import BaseModel, Field


class AdjudicacionListItem(BaseModel):
    """A real award (`core.adjudicacion`) with its tender, supplier and buyer names."""

    id: int
    licitacion_id: int | None = None
    licitacion_codigo: str | None = None
    licitacion_nombre: str | None = None
    proveedor_id: int | None = None
    proveedor_rut: str | None = None
    proveedor_razon_social: str | None = None
    organismo_id: int | None = None
    organismo_nombre: str | None = None
    monto_adjudicado: float | None = Field(None, description="Awarded amount, in CLP.")
    fecha_adjudicacion: datetime | None = None
    desviacion_precio_referencial: float | None = Field(
        None, description="(awarded / estimated - 1) * 100; negative = below the reference price."
    )
