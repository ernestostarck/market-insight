from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="A unique, machine-readable error code.")
    message: str = Field(..., description="A human-readable error message.")
    request_id: str | None = Field(None, description="The unique ID of the request.")


class ErrorResponse(BaseModel):
    error: ErrorDetail
