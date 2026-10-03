from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def test_settings_normalizes_environment_casing() -> None:
    settings = Settings(_env_file=None, ENVIRONMENT="  PRODUCTION  ", SECRET_KEY="a-real-random-secret-with-at-least-32-chars")

    assert settings.environment == "production"


def test_settings_allows_default_secret_key_outside_production() -> None:
    settings = Settings(_env_file=None, ENVIRONMENT="development")

    assert settings.secret_key == "change-me-in-production"


def test_settings_rejects_default_secret_key_in_production() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, ENVIRONMENT="production", SECRET_KEY="change-me-in-production")


def test_settings_accepts_real_secret_key_in_production() -> None:
    settings = Settings(_env_file=None, ENVIRONMENT="production", SECRET_KEY="a-real-random-secret-with-at-least-32-chars")

    assert settings.environment == "production"
    assert settings.secret_key == "a-real-random-secret-with-at-least-32-chars"


def test_cors_origins_splits_and_trims() -> None:
    settings = Settings(_env_file=None, BACKEND_CORS_ORIGINS=" http://a.test , http://b.test ,, ")

    assert settings.cors_origins == ["http://a.test", "http://b.test"]
