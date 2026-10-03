import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Account email, used as the login username.")


class UserCreate(UserBase):
    password: str = Field(..., description="Plain-text password; hashed with bcrypt before storage.")


class User(UserBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3b046957-d30a-43f7-84d8-7099e3b1120d",
                "email": "analista@marketinsight.cl",
                "is_active": True,
                "created_at": "2026-08-19T21:06:35.267573Z",
                "updated_at": "2026-08-19T21:06:35.267573Z",
            }
        },
    )

    id: uuid.UUID = Field(..., description="Internal user identifier.")
    is_active: bool = Field(..., description="Whether the account can authenticate.")
    created_at: datetime
    updated_at: datetime


# -- Profile, preferences, sessions, audit and admin (security hardening) ---------------

Theme = Literal["light", "dark", "system"]
Role = Literal["admin", "analyst"]


class UserPreferences(BaseModel):
    """Per-user settings applied by the web app. Unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")

    theme: Theme = "system"
    default_page_size: Literal[10, 25, 50, 100] = 10
    landing_page: Literal["/dashboard", "/mercado", "/licitaciones", "/proveedores", "/rubros"] = "/dashboard"
    default_segmento: str | None = Field(None, max_length=128, description="cat:<code> or concept:<code>.")
    compact_tables: bool = False


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    job_title: str | None = None
    role: Role
    is_active: bool
    mfa_enabled: bool
    preferences: UserPreferences
    created_at: datetime
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    password_changed_at: datetime | None = None

    @field_validator("preferences", mode="before")
    @classmethod
    def _merge_defaults(cls, value: Any) -> Any:
        # Stored JSON may predate newer keys or contain stale ones.
        known = UserPreferences.model_fields
        return {k: v for k, v in (value or {}).items() if k in known}


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(None, max_length=120)
    job_title: str | None = Field(None, max_length=120)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)


class PasswordPolicyCheck(BaseModel):
    password: str = Field(..., max_length=128)


class LoginResponse(BaseModel):
    """Either a session (`access_token`) or, for MFA accounts, a challenge (`mfa_token`)."""

    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = Field(None, description="Access-token lifetime, in seconds.")
    mfa_required: bool = False
    mfa_token: str | None = Field(None, description="Send with the TOTP code to /auth/mfa/verify.")


class MfaVerify(BaseModel):
    mfa_token: str
    code: str = Field(..., min_length=6, max_length=8)


class MfaCode(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MfaDisable(BaseModel):
    password: str = Field(..., max_length=128)
    code: str = Field(..., min_length=6, max_length=8)


class MfaSetupResponse(BaseModel):
    secret: str = Field(..., description="Base32 secret, for manual entry in the authenticator app.")
    otpauth_uri: str = Field(..., description="otpauth:// URI to render as a QR code.")


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool = False


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    event: str
    success: bool
    actor_email: str | None = None
    user_id: uuid.UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class AdminUserRead(UserProfile):
    failed_login_attempts: int = 0
    locked_until: datetime | None = None


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., max_length=128)
    full_name: str | None = Field(None, max_length=120)
    job_title: str | None = Field(None, max_length=120)
    role: Role = "analyst"


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(None, max_length=120)
    job_title: str | None = Field(None, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    unlock: bool | None = Field(None, description="Clear failed attempts and any lockout.")
    reset_mfa: bool | None = Field(None, description="Disable MFA (lost device).")
    revoke_sessions: bool | None = Field(None, description="Sign the user out everywhere.")
