"""Contract tests for the hardened auth endpoints (AuthService is faked: no DB)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.db.dependencies import get_auth_service, get_current_user
from app.main import app
from app.models.user import User as UserModel
from app.models.user import UserSession
from app.services.auth import IssuedSession, MfaChallenge


def _user(**overrides) -> UserModel:
    now = datetime.now(timezone.utc)
    values = dict(
        id=uuid.uuid4(),
        email="analista@marketinsight.cl",
        hashed_password=get_password_hash("Licitaciones#2026!"),
        is_active=True,
        role="analyst",
        preferences={},
        mfa_enabled=False,
        token_version=0,
        failed_login_attempts=0,
        created_at=now,
        updated_at=now,
    )
    values.update(overrides)
    return UserModel(**values)


class _FakeAuthService:
    def __init__(self, user: UserModel, *, mfa: bool = False):
        self.user = user
        self.mfa = mfa
        self.revoked: list[uuid.UUID] = []

    def _issued(self) -> IssuedSession:
        session = UserSession(
            id=uuid.uuid4(),
            user_id=self.user.id,
            refresh_token_hash="x" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        )
        return IssuedSession(access_token="access-token", refresh_token="refresh-secret", session=session, user=self.user)

    async def authenticate(self, email, password, request):
        if password != "Licitaciones#2026!":
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
        return MfaChallenge(mfa_token="mfa-token") if self.mfa else self._issued()

    async def verify_mfa_challenge(self, mfa_token, code, request):
        if code != "123456":
            raise HTTPException(status_code=401, detail="Código de verificación incorrecto.")
        return self._issued()

    async def refresh(self, refresh_token, request):
        if refresh_token != "refresh-secret":
            raise HTTPException(status_code=401, detail="La sesión expiró.")
        return self._issued()

    async def revoke_session(self, session_id, *, user_id, reason):
        self.revoked.append(session_id)
        return True


def _client(service: _FakeAuthService, *, authenticated: bool = False) -> TestClient:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_auth_service] = lambda: service
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: service.user
    return TestClient(app)


def test_public_registration_is_disabled() -> None:
    client = _client(_FakeAuthService(_user()))

    response = client.post("/api/v1/auth/register", json={"email": "x@y.cl", "password": "Whatever#2026!"})

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_login_returns_short_lived_token_and_httponly_refresh_cookie() -> None:
    client = _client(_FakeAuthService(_user()))

    response = client.post(
        "/api/v1/auth/login", data={"username": "analista@marketinsight.cl", "password": "Licitaciones#2026!"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "access-token"
    assert body["expires_in"] == 15 * 60
    assert body["mfa_required"] is False
    assert "refresh-secret" not in response.text  # the refresh token never reaches JavaScript
    cookie = response.headers["set-cookie"]
    assert "mi_refresh=refresh-secret" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert response.headers["cache-control"] == "no-store"
    app.dependency_overrides.clear()


def test_login_with_wrong_password_is_rejected() -> None:
    client = _client(_FakeAuthService(_user()))

    response = client.post("/api/v1/auth/login", data={"username": "analista@marketinsight.cl", "password": "nope"})

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    app.dependency_overrides.clear()


def test_mfa_account_gets_a_challenge_then_a_session() -> None:
    client = _client(_FakeAuthService(_user(mfa_enabled=True), mfa=True))

    first = client.post(
        "/api/v1/auth/login", data={"username": "analista@marketinsight.cl", "password": "Licitaciones#2026!"}
    )
    assert first.status_code == 200
    assert first.json()["mfa_required"] is True
    assert first.json()["access_token"] is None
    assert "set-cookie" not in first.headers

    bad = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": "mfa-token", "code": "000000"})
    assert bad.status_code == 401

    ok = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": "mfa-token", "code": "123456"})
    assert ok.status_code == 200
    assert ok.json()["access_token"] == "access-token"
    app.dependency_overrides.clear()


def test_refresh_without_valid_cookie_clears_it() -> None:
    client = _client(_FakeAuthService(_user()))

    response = client.post("/api/v1/auth/refresh", cookies={"mi_refresh": "stolen-or-expired"})

    assert response.status_code == 401
    assert 'mi_refresh=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
    app.dependency_overrides.clear()


def test_me_exposes_profile_but_never_secrets() -> None:
    user = _user(mfa_secret_encrypted="encrypted-secret")
    client = _client(_FakeAuthService(user), authenticated=True)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["role"] == "analyst"
    assert body["preferences"]["theme"] == "system"
    for secret_field in ("hashed_password", "mfa_secret_encrypted", "token_version", "failed_login_attempts"):
        assert secret_field not in body
    app.dependency_overrides.clear()


def test_preferences_reject_unknown_keys() -> None:
    client = _client(_FakeAuthService(_user()), authenticated=True)

    response = client.put("/api/v1/auth/me/preferences", json={"theme": "dark", "is_admin": True})

    assert response.status_code == 422
    app.dependency_overrides.clear()


def test_admin_endpoints_forbid_analysts() -> None:
    client = _client(_FakeAuthService(_user(role="analyst")), authenticated=True)

    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.get("/api/v1/admin/audit").status_code == 403
    app.dependency_overrides.clear()


def test_protected_endpoints_require_a_token() -> None:
    app.dependency_overrides.clear()
    client = TestClient(app)

    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/admin/users").status_code == 401
