"""Credential and token primitives.

- Passwords: Argon2id (bcrypt hashes from before still verify and are upgraded on login).
- Access tokens: short-lived HS256 JWTs with issuer/audience/type/jti claims. The
  user's `token_version` and session id travel in the token so a password change,
  "sign out everywhere" or a revoked session invalidates it server-side.
- Refresh tokens: 256-bit random opaque values; only their SHA-256 is stored.
- MFA: RFC 6238 TOTP (stdlib only), secrets encrypted at rest with Fernet.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_MFA = "mfa_challenge"

# Verified against when the account doesn't exist, so a login for an unknown email
# takes as long as one for a real account (no user enumeration through timing).
_DUMMY_HASH = pwd_context.hash(secrets.token_urlsafe(16))


# -- Passwords ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def verify_password_constant_time(plain_password: str, hashed_password: str | None) -> bool:
    if hashed_password is None:
        pwd_context.verify(plain_password, _DUMMY_HASH)
        return False
    return verify_password(plain_password, hashed_password)


def password_needs_rehash(hashed_password: str) -> bool:
    return pwd_context.needs_update(hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


_COMMON_PASSWORDS = {
    "password", "contraseña", "contrasena", "123456789012", "qwertyuiop12",
    "administrador", "marketinsight", "chilecompra", "bienvenido123", "password1234",
}


def password_policy_errors(password: str, *, email: str | None = None) -> list[str]:
    """Human-readable reasons a password is rejected (empty list = acceptable)."""
    settings = get_settings()
    errors: list[str] = []
    if len(password) < settings.password_min_length:
        errors.append(f"Debe tener al menos {settings.password_min_length} caracteres.")
    if len(password) > 128:
        errors.append("No puede superar 128 caracteres.")
    if not re.search(r"[a-záéíóúñ]", password):
        errors.append("Debe incluir una letra minúscula.")
    if not re.search(r"[A-ZÁÉÍÓÚÑ]", password):
        errors.append("Debe incluir una letra mayúscula.")
    if not re.search(r"\d", password):
        errors.append("Debe incluir un número.")
    if not re.search(r"[^\w\s]|_", password):
        errors.append("Debe incluir un símbolo (por ejemplo ! # $ %).")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        errors.append("Es una contraseña demasiado común.")
    if email:
        local_part = email.split("@", 1)[0].lower()
        if len(local_part) >= 4 and local_part in lowered:
            errors.append("No puede contener tu nombre de usuario.")
    return errors


# -- Access tokens -----------------------------------------------------------------------

def create_access_token(
    subject: Any,
    expires_delta: timedelta | None = None,
    *,
    token_version: int = 0,
    session_id: str | None = None,
    role: str | None = None,
    token_type: str = TOKEN_TYPE_ACCESS,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    claims: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": uuid.uuid4().hex,
        "typ": token_type,
        "ver": token_version,
    }
    if session_id:
        claims["sid"] = session_id
    if role:
        claims["role"] = role
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def decode_token_claims(token: str, *, token_type: str = TOKEN_TYPE_ACCESS) -> dict[str, Any] | None:
    """Validated claims, or None for a forged/expired/foreign/wrong-type token."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except JWTError:
        return None
    if claims.get("typ") != token_type:
        return None
    return claims


def decode_access_token(token: str) -> str | None:
    claims = decode_token_claims(token)
    return claims.get("sub") if claims else None


# -- Refresh tokens ----------------------------------------------------------------------

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# -- Secrets at rest ---------------------------------------------------------------------

def _fernet() -> Fernet:
    key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=b"market-insight/mfa", info=b"totp-secret"
    ).derive(get_settings().secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str | None:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return None


# -- TOTP (RFC 6238) ---------------------------------------------------------------------

_TOTP_STEP = 30
_TOTP_DIGITS = 6


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _totp_at(secret: str, counter: int) -> str:
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 10**_TOTP_DIGITS
    return str(code).zfill(_TOTP_DIGITS)


def verify_totp(secret: str, code: str, *, window: int = 1, at: float | None = None) -> bool:
    """Accept the current code and ±`window` steps of clock drift, in constant time."""
    code = re.sub(r"\s", "", code or "")
    if not re.fullmatch(r"\d{6}", code):
        return False
    counter = int((at if at is not None else time.time()) // _TOTP_STEP)
    return any(
        hmac.compare_digest(_totp_at(secret, counter + delta), code)
        for delta in range(-window, window + 1)
    )


def totp_provisioning_uri(secret: str, account: str) -> str:
    issuer = get_settings().mfa_issuer
    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={_TOTP_DIGITS}&period={_TOTP_STEP}"
    )
