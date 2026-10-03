from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrdenDeCompraBase(BaseModel):
    title: str | None = Field(None, description="Purchase order title/description.")
    amount: float | None = Field(None, description="Total order amount, in CLP.")
    purchase_date: datetime | None = Field(None, description="Date the order was issued.")


class OrdenDeCompraCreate(OrdenDeCompraBase):
    title: str = Field(..., description="Purchase order title/description.")


class OrdenDeCompraUpdate(OrdenDeCompraBase):
    pass


class OrdenDeCompraInDBBase(OrdenDeCompraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="Internal numeric identifier.")
    title: str = Field(..., description="Purchase order title/description.")


class OrdenDeCompra(OrdenDeCompraInDBBase):
    """Properties to return to the client."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 512,
                "title": "OC-2026-000512 Equipos de monitoreo",
                "amount": 2350000.0,
                "purchase_date": "2026-03-10T00:00:00Z",
            }
        },
    )


class OrdenDeCompraInDB(OrdenDeCompraInDBBase):
    """Properties stored in DB."""

    pass
