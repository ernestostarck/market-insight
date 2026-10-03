from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .organismo import Organismo


class LicitacionBase(BaseModel):
    codigo: str | None = Field(None, description="ChileCompra tender code (e.g. 1234-56-LE26).")
    nombre: str | None = Field(None, description="Tender title.")
    descripcion: str | None = Field(None, description="Tender description.")
    estado: str | None = Field(None, description="Tender status (e.g. publicada, cerrada, adjudicada).")
    fecha_publicacion: datetime | None = Field(None, description="Date the tender was published.")
    fecha_cierre: datetime | None = Field(None, description="Bid submission deadline.")
    monto_estimado: float | None = Field(None, description="Estimated tender amount, in CLP.")


class LicitacionCreate(LicitacionBase):
    codigo: str = Field(..., description="ChileCompra tender code (e.g. 1234-56-LE26).")
    nombre: str = Field(..., description="Tender title.")


class LicitacionUpdate(LicitacionBase):
    pass


class LicitacionInDBBase(LicitacionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="Internal numeric identifier.")
    codigo: str | None = Field(default=None, description="ChileCompra tender code (e.g. 1234-56-LE26).")
    organismo_id: int | None = Field(default=None, description="Id of the buying agency (organismo) that published it.")


class Licitacion(LicitacionInDBBase):
    """Properties to return to the client."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 123,
                "codigo": "1234-56-LE26",
                "nombre": "Adquisicion de equipos de seguridad geriatrica",
                "descripcion": "Compra de camas y sillas de ruedas para centros geriatricos.",
                "estado": "publicada",
                "fecha_publicacion": "2026-01-05T09:00:00Z",
                "fecha_cierre": "2026-02-05T18:00:00Z",
                "monto_estimado": 45000000.0,
                "organismo_id": 7,
                "organismo": None,
            }
        },
    )

    organismo: Organismo | None = None
    categoria: str | None = Field(
        None, description="Rubro leaf name (real, from core.categoria via categoria_id)."
    )


class LicitacionInDB(LicitacionInDBBase):
    """Properties stored in DB."""

    pass
