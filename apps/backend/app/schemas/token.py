from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    )

    access_token: str = Field(..., description="JWT to send as `Authorization: Bearer <token>`.")
    token_type: str = Field(..., description="Always `bearer`.")


class TokenData(BaseModel):
    email: Optional[str] = Field(None, description="Email encoded in the token's `sub` claim.")
