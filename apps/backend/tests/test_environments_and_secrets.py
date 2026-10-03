"""Tests for Phase 10: Environments, Configuration, and Secrets Management (10.1, 10.2, 10.3)."""

from pathlib import Path
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.core.exceptions import AppException
from app.core.logging import redact_text, redact_value, REDACTED
from app.core.settings import Settings
from app.main import app


# ---------------------------------------------------------------------------
# 10.1 & 10.2: Settings & Environment Normalization
# ---------------------------------------------------------------------------

def test_settings_environment_aliases():
    """Verify that APP_ENV and ENVIRONMENT are recognized interchangeably."""
    s1 = Settings(_env_file=None, ENVIRONMENT="development")
    assert s1.environment == "development"

    s2 = Settings(_env_file=None, APP_ENV="staging", SECRET_KEY="valid-secret-key-32-chars-staging!!")
    assert s2.environment == "staging"

    s3 = Settings(_env_file=None, APP_ENV="  PRODUCTION  ", SECRET_KEY="valid-secret-key-32-chars-prod!!")
    assert s3.environment == "production"


def test_settings_llm_api_key_alias():
    """Verify LLM_API_KEY populates the LLM configuration and is accessible via property."""
    s = Settings(_env_file=None, LLM_API_KEY="sk-mock-llm-token-12345")
    assert s.openai_api_key == "sk-mock-llm-token-12345"
    assert s.llm_api_key == "sk-mock-llm-token-12345"


# ---------------------------------------------------------------------------
# 10.3: Secret Key Enforcement in Staging & Production
# ---------------------------------------------------------------------------

def test_secret_key_allowed_default_in_dev_and_test():
    """In development and test, the default placeholder secret key is acceptable."""
    s_dev = Settings(_env_file=None, ENVIRONMENT="development")
    assert s_dev.secret_key == "change-me-in-production"

    s_test = Settings(_env_file=None, ENVIRONMENT="test")
    assert s_test.secret_key == "change-me-in-production"


def test_secret_key_rejected_in_production_with_placeholder():
    """In production, using the placeholder secret key must raise a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, ENVIRONMENT="production", SECRET_KEY="change-me-in-production")
    assert "SECRET_KEY is still set to the insecure placeholder" in str(exc_info.value)


def test_secret_key_rejected_in_staging_with_placeholder():
    """In staging, using the placeholder secret key must also raise a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, APP_ENV="staging", SECRET_KEY="change-me-in-production")
    assert "SECRET_KEY is still set to the insecure placeholder" in str(exc_info.value)


def test_secret_key_accepted_in_production_with_strong_key():
    """A high-entropy secret key is accepted in production."""
    strong_key = "a" * 32
    s = Settings(_env_file=None, ENVIRONMENT="production", SECRET_KEY=strong_key)
    assert s.secret_key == strong_key


# ---------------------------------------------------------------------------
# 10.3: Logging and Redaction Hygiene
# ---------------------------------------------------------------------------

def test_redact_sensitive_dictionary_keys():
    """Ensure sensitive dictionary keys are masked unconditionally."""
    payload = {
        "username": "alice",
        "password": "SuperSecretPassword123!",
        "token": "jwt-token-abcdefg",
        "api_key": "chilecompra-private-key",
        "authorization": "Bearer eyJhbGciOi...",
        "public_field": "visible",
    }
    redacted = redact_value(payload)
    assert redacted["username"] == "alice"
    assert redacted["password"] == REDACTED
    assert redacted["token"] == REDACTED
    assert redacted["api_key"] == REDACTED
    assert redacted["authorization"] == REDACTED
    assert redacted["public_field"] == "visible"


def test_redact_url_credentials():
    """Ensure database and redis URLs with passwords have the password masked."""
    db_url = "postgresql+psycopg://market_insight_app:super_secret_pg_pwd@postgres:5432/market_insight"
    redis_url = "redis://:secret_redis_pass@redis:6379/0"

    redacted_db = redact_text(db_url)
    redacted_redis = redact_text(redis_url)

    assert "super_secret_pg_pwd" not in redacted_db
    assert REDACTED in redacted_db
    assert "secret_redis_pass" not in redacted_redis
    assert REDACTED in redacted_redis


def test_redact_bearer_tokens_in_text():
    """Ensure free-text authorization tokens are scrubbed."""
    raw_text = "Failed request with header Bearer abcdef1234567890xyz and cookie"
    redacted = redact_text(raw_text)
    assert "abcdef1234567890xyz" not in redacted
    assert "Bearer ***REDACTED***" in redacted


# ---------------------------------------------------------------------------
# 10.3: Error Handling Hygiene (No Leaks to Client)
# ---------------------------------------------------------------------------

def test_unhandled_exception_does_not_leak_internals():
    """Ensure unhandled 500 errors do not expose stack traces or internal DB info."""
    client = TestClient(app, raise_server_exceptions=False)

    # Trigger a custom endpoint error or route that raises
    @app.get("/test-internal-error")
    def trigger_error():
        raise RuntimeError("Internal DB connection failed at postgresql://user:secret@host:5432")

    response = client.get("/test-internal-error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected internal server error occurred."
    assert "secret" not in response.text
    assert "Traceback" not in response.text


# ---------------------------------------------------------------------------
# 10.1 & 10.3: File Hygiene (.gitignore and .dockerignore)
# ---------------------------------------------------------------------------

def test_dockerignore_and_gitignore_hygiene():
    """Verify that .dockerignore and .gitignore exist and protect sensitive files."""
    repo_root = Path(__file__).resolve().parents[3]

    root_dockerignore = repo_root / ".dockerignore"
    backend_dockerignore = repo_root / "apps" / "backend" / ".dockerignore"
    frontend_dockerignore = repo_root / "apps" / "frontend" / ".dockerignore"
    root_gitignore = repo_root / ".gitignore"

    assert root_dockerignore.exists(), "Root .dockerignore is missing"
    assert backend_dockerignore.exists(), "apps/backend/.dockerignore is missing"
    assert frontend_dockerignore.exists(), "apps/frontend/.dockerignore is missing"
    assert root_gitignore.exists(), ".gitignore is missing"

    root_dockerignore_content = root_dockerignore.read_text(encoding="utf-8")
    assert ".env" in root_dockerignore_content
    assert "*.pem" in root_dockerignore_content
    assert "*.key" in root_dockerignore_content

    root_gitignore_content = root_gitignore.read_text(encoding="utf-8")
    assert ".env.*" in root_gitignore_content
    assert "!.env.example" in root_gitignore_content


# ---------------------------------------------------------------------------
# 10.2: validate-env Script Verification
# ---------------------------------------------------------------------------

def test_validate_env_script_integration():
    """Verify validate_env script accurately detects valid and invalid configs."""
    import sys
    repo_root = Path(__file__).resolve().parents[3]
    scripts_dir = repo_root / "infrastructure" / "scripts"
    sys.path.insert(0, str(scripts_dir))

    from importlib import import_module
    validate_env = import_module("validate-env")

    # 1. Valid development template
    dev_vars = validate_env.parse_env_file(repo_root / ".env.example")
    dev_errors = validate_env.validate_environment("development", dev_vars, is_template=True)
    assert len(dev_errors) == 0

    # 2. Valid staging template
    staging_vars = validate_env.parse_env_file(repo_root / ".env.staging.example")
    staging_errors = validate_env.validate_environment("staging", staging_vars, is_template=True)
    assert len(staging_errors) == 0

    # 3. Insecure placeholders caught
    bad_prod_vars = {
        "APP_ENV": "production",
        "PUBLIC_BASE_URL": "https://app.example.com",
        "SECRET_KEY": "change-me-in-production",
        "CHILECOMPRA_API_KEY": "dummy",
        "POSTGRES_PASSWORD": "market_insight_dev",
        "MARKET_INSIGHT_ADMIN_PASSWORD": "admin",
        "MARKET_INSIGHT_APP_PASSWORD": "app",
        "MARKET_INSIGHT_READONLY_PASSWORD": "ro",
        "REDIS_PASSWORD": "market_insight_redis_dev",
        "MINIO_ROOT_USER": "marketinsight",
        "MINIO_ROOT_PASSWORD": "marketinsight-dev-password",
        "GRAFANA_ADMIN_PASSWORD": "admin",
        "ALERT_WEBHOOK_TOKEN": "token",
    }
    prod_errors = validate_env.validate_environment("production", bad_prod_vars, check_placeholders=True)
    assert any("SECRET_KEY" in err for err in prod_errors)
    assert any("POSTGRES_PASSWORD" in err for err in prod_errors)
