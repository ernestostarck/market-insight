from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"), extra="ignore"
    )

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )
    app_name: str = Field(default="MercadoInsight API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    debug: bool = Field(default=False, alias="DEBUG")

    secret_key: str = Field(
        default=_INSECURE_DEFAULT_SECRET_KEY, alias="SECRET_KEY"
    )
    # Short-lived access token; the session is extended through a rotating,
    # server-side refresh token (httpOnly cookie) up to `session_max_hours`.
    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    session_max_hours: int = Field(default=8, alias="SESSION_MAX_HOURS")
    jwt_issuer: str = Field(default="market-insight-api", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="market-insight-web", alias="JWT_AUDIENCE")
    refresh_cookie_secure: bool | None = Field(
        default=None,
        alias="REFRESH_COOKIE_SECURE",
        description="Defaults to True outside development (cookie only sent over HTTPS).",
    )

    # Credential protection
    login_max_attempts: int = Field(default=5, alias="LOGIN_MAX_ATTEMPTS")
    login_lockout_minutes: int = Field(default=15, alias="LOGIN_LOCKOUT_MINUTES")
    auth_rate_limit_per_minute: int = Field(default=10, alias="AUTH_RATE_LIMIT_PER_MINUTE")
    password_min_length: int = Field(default=12, alias="PASSWORD_MIN_LENGTH")
    mfa_issuer: str = Field(default="Market Insight", alias="MFA_ISSUER")

    # Application firewall
    firewall_enabled: bool = Field(default=True, alias="FIREWALL_ENABLED")
    firewall_ip_allowlist: str = Field(
        default="",
        alias="FIREWALL_IP_ALLOWLIST",
        description="Comma-separated IPs/CIDRs; when set, every other client is refused.",
    )
    firewall_ip_denylist: str = Field(default="", alias="FIREWALL_IP_DENYLIST")
    firewall_ban_threshold: int = Field(
        default=20,
        alias="FIREWALL_BAN_THRESHOLD",
        description="Blocked/unauthorized requests from one IP (per 10 min) before a temporary ban.",
    )
    firewall_ban_seconds: int = Field(default=900, alias="FIREWALL_BAN_SECONDS")
    max_request_body_bytes: int = Field(default=1_048_576, alias="MAX_REQUEST_BODY_BYTES")
    max_upload_body_bytes: int = Field(default=26_214_400, alias="MAX_UPLOAD_BODY_BYTES")
    allowed_hosts: str = Field(
        default="*",
        alias="ALLOWED_HOSTS",
        description="Comma-separated Host header values accepted (e.g. api.example.com).",
    )
    trusted_proxies: str = Field(
        default="127.0.0.1,::1",
        alias="TRUSTED_PROXIES",
        description="Proxies whose X-Forwarded-For is trusted to identify the real client IP.",
    )
    backend_cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:80",
        alias="BACKEND_CORS_ORIGINS",
    )

    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_WINDOW_SECONDS"
    )

    chilecompra_api_url: str = Field(
        default="https://api.mercadopublico.cl/servicios/v1/publico",
        validation_alias=AliasChoices("CHILECOMPRA_API_URL", "CHILECOMPRA_BASE_URL"),
    )
    chilecompra_api_ticket: str = Field(
        default="",
        validation_alias=AliasChoices("CHILECOMPRA_API_TICKET", "CHILECOMPRA_API_KEY"),
    )
    chilecompra_timeout: float = Field(default=30.0, alias="CHILECOMPRA_TIMEOUT")
    chilecompra_max_retries: int = Field(default=3, alias="CHILECOMPRA_MAX_RETRIES")
    chilecompra_retry_delay: float = Field(default=0.5, alias="CHILECOMPRA_RETRY_DELAY")

    database_url: str = Field(
        default="postgresql+psycopg://market_insight_app:market_insight_app_dev@postgres:5432/market_insight",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://:market_insight_redis_dev@redis:6379/0", alias="REDIS_URL"
    )
    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="marketinsight", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(
        default="marketinsight-dev-password", alias="MINIO_SECRET_KEY"
    )
    minio_bucket_public_documents: str = Field(
        default="documents-public", alias="MINIO_BUCKET_PUBLIC_DOCUMENTS"
    )
    minio_bucket_private_documents: str = Field(
        default="documents-private", alias="MINIO_BUCKET_PRIVATE_DOCUMENTS"
    )
    minio_bucket_attachments: str = Field(
        default="attachments", alias="MINIO_BUCKET_ATTACHMENTS"
    )
    minio_bucket_ml_models: str = Field(
        default="ml-models", alias="MINIO_BUCKET_ML_MODELS"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="auto", alias="LOG_FORMAT")
    log_sql: bool = Field(default=False, alias="LOG_SQL")

    # Sentry error tracking (Fase 8.12)
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_environment: str | None = Field(default=None, alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=1.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    sentry_profiles_sample_rate: float = Field(default=1.0, alias="SENTRY_PROFILES_SAMPLE_RATE")

    # OpenTelemetry distributed tracing (Fase 8.13)
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="market-insight-backend", alias="OTEL_SERVICE_NAME")
    otel_exporter_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    # Observability Security (Fase 8 - Observability Security)
    metrics_auth_token: str | None = Field(default=None, alias="METRICS_AUTH_TOKEN")
    alert_webhook_token: str | None = Field(default=None, alias="ALERT_WEBHOOK_TOKEN")

    # LLM & AI Gateway (Fase 9.11)
    llm_provider: str = Field(default="local", alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
    )
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model_name: str = Field(default="claude-3-5-sonnet-latest", alias="LLM_MODEL_NAME")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: Any) -> str:
        return str(value).strip().lower()

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        import sys
        val = str(value)
        if sys.platform == "win32":
            val = val.replace("@postgres:", "@127.0.0.1:")
            if "postgresql+psycopg://" in val:
                val = val.replace("postgresql+psycopg://", "postgresql+asyncpg://")
            elif val.startswith("postgresql://"):
                val = val.replace("postgresql://", "postgresql+asyncpg://", 1)
        return val

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_redis_url(cls, value: Any) -> str:
        import sys
        val = str(value)
        if sys.platform == "win32":
            val = val.replace("@redis:", "@127.0.0.1:")
        return val

    @field_validator("minio_endpoint", mode="before")
    @classmethod
    def normalize_minio_endpoint(cls, value: Any) -> str:
        import sys
        val = str(value)
        if sys.platform == "win32" and val.startswith("minio:"):
            val = val.replace("minio:", "127.0.0.1:", 1)
        return val

    @model_validator(mode="after")
    def reject_insecure_secret_key_in_production(self) -> "Settings":
        if self.environment in ("production", "staging"):
            if self.secret_key == _INSECURE_DEFAULT_SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY is still set to the insecure placeholder value "
                    f"'{_INSECURE_DEFAULT_SECRET_KEY}'. Set a real random SECRET_KEY "
                    f"before running with ENVIRONMENT={self.environment}."
                )
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters outside development.")
            if self.debug:
                raise ValueError(f"DEBUG must be false with ENVIRONMENT={self.environment}.")
        return self

    @property
    def is_development(self) -> bool:
        return self.environment in ("development", "dev", "local", "test", "testing")

    @property
    def secure_cookies(self) -> bool:
        if self.refresh_cookie_secure is not None:
            return self.refresh_cookie_secure
        return not self.is_development

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return self._split(self.allowed_hosts) or ["*"]

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def chilecompra_api_key(self) -> str:
        return self.chilecompra_api_ticket

    @property
    def chilecompra_base_url(self) -> str:
        return self.chilecompra_api_url

    @property
    def llm_api_key(self) -> str | None:
        return self.openai_api_key or self.anthropic_api_key


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
