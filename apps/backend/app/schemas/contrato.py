from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContratoBase(BaseModel):
    title: str | None = Field(None, description="Contract title/description.")
    amount: float | None = Field(None, description="Total contract amount, in CLP.")
    start_date: datetime | None = Field(None, description="Contract start date.")
    end_date: datetime | None = Field(None, description="Contract end date.")


class ContratoCreate(ContratoBase):
    title: str = Field(..., description="Contract title/description.")


class ContratoUpdate(ContratoBase):
    pass


class ContratoInDBBase(ContratoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="Internal numeric identifier.")
    title: str = Field(..., description="Contract title/description.")


class Contrato(ContratoInDBBase):
    """Properties to return to the client."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 301,
                "title": "Suministro de sillas de ruedas 2026",
                "amount": 15000000.0,
                "start_date": "2026-01-15T00:00:00Z",
                "end_date": "2026-12-31T00:00:00Z",
            }
        },
    )


class ContratoInDB(ContratoInDBBase):
    """Properties stored in DB."""

    pass
