from pydantic import BaseModel, ConfigDict, Field


class CompradorBase(BaseModel):
    name: str | None = Field(None, description="Full name of the buyer/purchasing officer.")
    region: str | None = Field(None, description="Region where the buyer operates.")


class CompradorCreate(CompradorBase):
    name: str = Field(..., description="Full name of the buyer/purchasing officer.")
    region: str = Field(..., description="Region where the buyer operates.")


class CompradorUpdate(CompradorBase):
    pass


class CompradorInDBBase(CompradorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="Internal numeric identifier.")
    name: str = Field(..., description="Full name of the buyer/purchasing officer.")


class Comprador(CompradorInDBBase):
    """Properties to return to the client."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {"id": 15, "name": "Maria Perez", "region": "Metropolitana"}
        },
    )


class CompradorInDB(CompradorInDBBase):
    """Properties stored in DB."""

    pass
