from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProveedorBase(BaseModel):
    rut: str | None = Field(None, description="RUT (Chilean tax ID) of the supplier.")
    razon_social: str | None = Field(None, description="Legal/registered business name.")
    nombre_fantasia: str | None = Field(
        None, description="Trade name, if different from razon_social."
    )


class ProveedorCreate(ProveedorBase):
    rut: str = Field(..., description="RUT (Chilean tax ID) of the supplier.")
    razon_social: str = Field(..., description="Legal/registered business name.")


class ProveedorUpdate(ProveedorBase):
    pass


class ProveedorInDBBase(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="Internal numeric identifier.")
    rut: str = Field(..., description="RUT (Chilean tax ID) of the supplier.")


class Proveedor(ProveedorInDBBase):
    """Properties to return to client."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "rut": "76.123.456-7",
                "razon_social": "Suministros Medicos del Sur SpA",
                "nombre_fantasia": "SuMedSur",
                "region": "Metropolitana de Santiago",
                "categoria_principal": "Equipos Médicos y Camas Clínicas",
                "fecha_registro": "2019-01-20T00:00:00Z",
                "total_licitaciones_participadas": 48,
                "total_adjudicaciones": 29,
                "tasa_exito": 60.4,
                "monto_total_adjudicado": 980200000.0,
            }
        },
    )

    region: str | None = Field(None, description="Registered region of the supplier.")
    categoria_principal: str | None = Field(
        None,
        description="Category the supplier has been awarded in most often. "
        "None if it has no awards yet.",
    )
    fecha_registro: datetime | None = Field(
        None, description="When the supplier was first ingested into the platform."
    )
    total_licitaciones_participadas: int = Field(
        0, description="Total number of ofertas (bids) submitted by this supplier."
    )
    total_adjudicaciones: int = Field(
        0, description="Total number of licitaciones awarded to this supplier."
    )
    tasa_exito: float | None = Field(
        None,
        description="Award rate in percent (total_adjudicaciones / "
        "total_licitaciones_participadas * 100). None if it has never bid.",
    )
    monto_total_adjudicado: float = Field(
        0, description="Sum of monto_adjudicado across every award to this supplier, in CLP."
    )


class ProveedorInDB(ProveedorInDBBase):
    """Properties stored in DB."""

    pass
