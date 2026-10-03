from pydantic import BaseModel, ConfigDict, Field


class OrganismoBase(BaseModel):
    nombre: str | None = Field(None, description="Name of the buying agency (organismo).")
    codigo: str | None = Field(None, description="ChileCompra organism code.")


class OrganismoCreate(OrganismoBase):
    pass


class OrganismoUpdate(OrganismoBase):
    pass


class OrganismoInDBBase(OrganismoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal numeric identifier.")
    codigo: str = Field(..., description="ChileCompra organism code.")


class Organismo(OrganismoInDBBase):
    """Properties to return to client."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 7,
                "codigo": "H12345",
                "nombre": "Servicio de Salud Metropolitano Sur",
            }
        },
    )


class OrganismoRanking(Organismo):
    """Organismo plus purchasing stats aggregated from core.licitacion/core.adjudicacion."""

    total_licitaciones: int = Field(0, description="Licitaciones published by this agency.")
    licitaciones_activas: int = Field(0, description="Licitaciones currently published (open).")
    monto_total_comprado: float = Field(0, description="Total awarded amount, in CLP.")
    categoria_principal: str | None = Field(
        None, description="Category this agency publishes most licitaciones in."
    )


class OrganismoInDB(OrganismoInDBBase):
    """Properties stored in DB."""

    pass
