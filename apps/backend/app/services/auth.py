"""Authentication flows: login (+ lockout, MFA), session issue/refresh/revoke, password
and MFA management. Every outcome is written to the security audit log."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core import security
from app.core.client_ip import client_ip
from app.core.settings import get_settings
from app.models.user import User, UserSession
from app.services import security_audit as audit

_redis: redis.Redis | None = None


def _redis_client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
    return _redis


def _now() -> datetime:
    return datetime.now(timezone.utc)


_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Correo o contraseña incorrectos.",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class IssuedSession:
    access_token: str
    refresh_token: str
    session: UserSession
    user: User


@dataclass
class MfaChallenge:
    mfa_token: str


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    # -- Brute-force throttling (per client IP, independent of the global rate limit) --

    async def enforce_auth_rate_limit(self, request: Request, scope: str) -> None:
        ip = client_ip(request)
        key = f"auth_rl:{scope}:{ip}:{int(time.time()) // 60}"
        try:
            client = _redis_client()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, 60)
        except Exception:
            return  # Redis down: the per-account lockout below still protects credentials.
        if count > self.settings.auth_rate_limit_per_minute:
            if count == self.settings.auth_rate_limit_per_minute + 1:
                await audit.record(audit.AUTH_RATE_LIMITED, request=request, success=False, detail={"scope": scope})
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Espera un minuto antes de volver a intentarlo.",
                headers={"Retry-After": "60"},
            )

    # -- Login -------------------------------------------------------------------------

    async def authenticate(self, email: str, password: str, request: Request) -> IssuedSession | MfaChallenge:
        await self.enforce_auth_rate_limit(request, "login")
        email = email.strip().lower()
        user = (
            await self.session.execute(select(User).where(func.lower(User.email) == email))
        ).scalars().first()

        if user is not None and user.locked_until and user.locked_until > _now():
            security.verify_password_constant_time(password, None)
            await audit.record(audit.LOGIN_BLOCKED_LOCKED, request=request, user_id=user.id, email=email, success=False)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="La cuenta está bloqueada temporalmente por intentos fallidos. "
                "Intenta más tarde o contacta a un administrador.",
            )

        valid = security.verify_password_constant_time(password, user.hashed_password if user else None)
        if user is None or not valid or not user.is_active:
            await self._register_failure(user, email, request, reason="inactive" if user and valid else "bad_credentials")
            raise _INVALID_CREDENTIALS

        if security.password_needs_rehash(user.hashed_password):
            user.hashed_password = security.get_password_hash(password)

        if user.mfa_enabled:
            await self.session.commit()
            token = security.create_access_token(
                user.id,
                timedelta(minutes=5),
                token_version=user.token_version,
                token_type=security.TOKEN_TYPE_MFA,
            )
            return MfaChallenge(mfa_token=token)

        return await self._complete_login(user, request, method="password")

    async def verify_mfa_challenge(self, mfa_token: str, code: str, request: Request) -> IssuedSession:
        await self.enforce_auth_rate_limit(request, "mfa")
        claims = security.decode_token_claims(mfa_token, token_type=security.TOKEN_TYPE_MFA)
        user = await self._user_from_claims(claims) if claims else None
        if user is None or not user.mfa_enabled or not user.mfa_secret_encrypted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El desafío MFA expiró. Inicia sesión otra vez.")
        secret = security.decrypt_secret(user.mfa_secret_encrypted)
        if secret is None or not security.verify_totp(secret, code):
            await self._register_failure(user, user.email, request, reason="bad_mfa_code", event=audit.MFA_CHALLENGE_FAILED)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código de verificación incorrecto.")
        return await self._complete_login(user, request, method="password+totp")

    async def _register_failure(
        self, user: User | None, email: str, request: Request, *, reason: str, event: str = audit.LOGIN_FAILED
    ) -> None:
        detail: dict = {"reason": reason}
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            detail["failed_attempts"] = user.failed_login_attempts
            if user.failed_login_attempts >= self.settings.login_max_attempts:
                # Lockout doubles with each further failure: 15, 30, 60 ... minutes (max 24 h).
                extra = user.failed_login_attempts - self.settings.login_max_attempts
                minutes = min(self.settings.login_lockout_minutes * (2**extra), 24 * 60)
                user.locked_until = _now() + timedelta(minutes=minutes)
                detail["locked_minutes"] = minutes
                await self.session.commit()
                await audit.record(audit.ACCOUNT_LOCKED, request=request, user_id=user.id, email=email, success=False, detail=detail)
            await self.session.commit()
        await audit.record(event, request=request, user_id=user.id if user else None, email=email, success=False, detail=detail)

    async def _complete_login(self, user: User, request: Request, *, method: str) -> IssuedSession:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = _now()
        user.last_login_ip = client_ip(request)
        issued = await self._issue_session(user, request)
        await audit.record(audit.LOGIN_SUCCESS, request=request, user_id=user.id, email=user.email, detail={"method": method})
        return issued

    # -- Sessions ----------------------------------------------------------------------

    async def _issue_session(self, user: User, request: Request) -> IssuedSession:
        refresh_token = security.generate_refresh_token()
        user_session = UserSession(
            id=uuid.uuid4(),
            user_id=user.id,
            refresh_token_hash=security.hash_token(refresh_token),
            ip_address=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:400],
            expires_at=_now() + timedelta(hours=self.settings.session_max_hours),
        )
        self.session.add(user_session)
        await self.session.commit()
        return IssuedSession(
            access_token=self._access_token(user, user_session),
            refresh_token=refresh_token,
            session=user_session,
            user=user,
        )

    def _access_token(self, user: User, user_session: UserSession) -> str:
        return security.create_access_token(
            user.id, token_version=user.token_version, session_id=str(user_session.id), role=user.role
        )

    async def refresh(self, refresh_token: str | None, request: Request) -> IssuedSession:
        await self.enforce_auth_rate_limit(request, "refresh")
        expired = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión expiró. Inicia sesión otra vez.")
        if not refresh_token:
            raise expired
        token_hash = security.hash_token(refresh_token)
        user_session = (
            await self.session.execute(select(UserSession).where(UserSession.refresh_token_hash == token_hash))
        ).scalars().first()

        if user_session is None:
            # A refresh token that was already rotated is being replayed: it was stolen.
            # Kill every session of that user.
            reused = (
                await self.session.execute(select(UserSession).where(UserSession.previous_token_hash == token_hash))
            ).scalars().first()
            if reused is not None:
                owner = await self.session.get(User, reused.user_id)
                await self.revoke_all_sessions(reused.user_id, reason="refresh_token_reuse")
                await audit.record(
                    audit.REFRESH_TOKEN_REUSE, request=request, user_id=reused.user_id,
                    email=owner.email if owner else None, success=False,
                )
            raise expired

        if user_session.revoked_at is not None or user_session.expires_at <= _now():
            raise expired
        user = await self.session.get(User, user_session.user_id)
        if user is None or not user.is_active:
            raise expired

        new_token = security.generate_refresh_token()
        user_session.previous_token_hash = user_session.refresh_token_hash
        user_session.refresh_token_hash = security.hash_token(new_token)
        user_session.last_seen_at = _now()
        user_session.ip_address = client_ip(request)
        await self.session.commit()
        return IssuedSession(
            access_token=self._access_token(user, user_session),
            refresh_token=new_token,
            session=user_session,
            user=user,
        )

    async def revoke_session(self, session_id: uuid.UUID, *, user_id: uuid.UUID, reason: str) -> bool:
        result = await self.session.execute(
            update(UserSession)
            .where(UserSession.id == session_id, UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=_now(), revoked_reason=reason)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def revoke_all_sessions(self, user_id: uuid.UUID, *, reason: str) -> None:
        await self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=_now(), revoked_reason=reason)
        )
        await self.session.execute(
            update(User).where(User.id == user_id).values(token_version=User.token_version + 1)
        )
        await self.session.commit()

    async def active_sessions(self, user_id: uuid.UUID) -> list[UserSession]:
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None), UserSession.expires_at > _now())
            .order_by(UserSession.last_seen_at.desc())
        )
        return list(result.scalars().all())

    # -- Token validation (used by get_current_user) ----------------------------------

    async def _user_from_claims(self, claims: dict) -> User | None:
        try:
            user_id = uuid.UUID(claims["sub"])
        except (KeyError, ValueError):
            return None
        user = await self.session.get(User, user_id)
        if user is None or not user.is_active or claims.get("ver") != user.token_version:
            return None
        return user

    async def user_from_access_token(self, token: str) -> tuple[User, uuid.UUID | None] | None:
        claims = security.decode_token_claims(token)
        if claims is None:
            return None
        user = await self._user_from_claims(claims)
        if user is None:
            return None
        session_id = None
        if claims.get("sid"):
            session_id = uuid.UUID(claims["sid"])
            user_session = await self.session.get(UserSession, session_id)
            if (
                user_session is None
                or user_session.revoked_at is not None
                or user_session.expires_at <= _now()
            ):
                return None
        return user, session_id

    # -- Password & MFA -----------------------------------------------------------------

    async def change_password(
        self, user: User, current_password: str, new_password: str, request: Request, *, keep_session: uuid.UUID | None
    ) -> None:
        await self.enforce_auth_rate_limit(request, "password")
        if not security.verify_password(current_password, user.hashed_password):
            await audit.record(audit.PASSWORD_CHANGE_FAILED, request=request, user_id=user.id, email=user.email, success=False)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual no es correcta.")
        errors = security.password_policy_errors(new_password, email=user.email)
        if security.verify_password(new_password, user.hashed_password):
            errors.append("La nueva contraseña debe ser distinta de la actual.")
        if errors:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"password": errors})
        user.hashed_password = security.get_password_hash(new_password)
        user.password_changed_at = _now()
        await self.session.commit()
        # Every other device must sign in again with the new password.
        await self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None), UserSession.id != keep_session)
            .values(revoked_at=_now(), revoked_reason="password_changed")
        )
        await self.session.commit()
        await audit.record(audit.PASSWORD_CHANGED, request=request, user_id=user.id, email=user.email)

    async def start_mfa_setup(self, user: User) -> tuple[str, str]:
        if user.mfa_enabled:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA ya está activado.")
        secret = security.generate_totp_secret()
        user.mfa_secret_encrypted = security.encrypt_secret(secret)
        await self.session.commit()
        return secret, security.totp_provisioning_uri(secret, user.email)

    async def enable_mfa(self, user: User, code: str, request: Request) -> None:
        await self.enforce_auth_rate_limit(request, "mfa")
        secret = security.decrypt_secret(user.mfa_secret_encrypted) if user.mfa_secret_encrypted else None
        if user.mfa_enabled or secret is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Primero inicia la configuración de MFA.")
        if not security.verify_totp(secret, code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código incorrecto. Revisa la hora del teléfono.")
        user.mfa_enabled = True
        await self.session.commit()
        await audit.record(audit.MFA_ENABLED, request=request, user_id=user.id, email=user.email)

    async def disable_mfa(self, user: User, password: str, code: str, request: Request) -> None:
        await self.enforce_auth_rate_limit(request, "mfa")
        secret = security.decrypt_secret(user.mfa_secret_encrypted) if user.mfa_secret_encrypted else None
        if (
            not user.mfa_enabled
            or secret is None
            or not security.verify_password(password, user.hashed_password)
            or not security.verify_totp(secret, code)
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña o código incorrectos.")
        user.mfa_enabled = False
        user.mfa_secret_encrypted = None
        await self.session.commit()
        await audit.record(audit.MFA_DISABLED, request=request, user_id=user.id, email=user.email)
