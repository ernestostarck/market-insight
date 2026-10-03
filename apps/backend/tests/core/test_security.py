from __future__ import annotations

from datetime import timedelta

from jose import jwt

from app.core.security import (
    ALGORITHM,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_MFA,
    _totp_at,
    create_access_token,
    decode_access_token,
    decode_token_claims,
    decrypt_secret,
    encrypt_secret,
    generate_refresh_token,
    generate_totp_secret,
    get_password_hash,
    hash_token,
    password_policy_errors,
    verify_password,
    verify_totp,
)
from app.core.settings import get_settings


def test_create_access_token_round_trips_subject() -> None:
    token = create_access_token(subject="user@example.com")

    assert decode_access_token(token) == "user@example.com"


def test_create_access_token_coerces_non_string_subject() -> None:
    token = create_access_token(subject=42)

    assert decode_access_token(token) == "42"


def _decode(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


def test_create_access_token_embeds_expiry_and_hardening_claims() -> None:
    payload = _decode(create_access_token(subject="user@example.com", token_version=3, session_id="s-1"))

    assert payload["sub"] == "user@example.com"
    assert {"exp", "iat", "nbf", "jti"} <= payload.keys()
    assert payload["typ"] == TOKEN_TYPE_ACCESS
    assert payload["ver"] == 3
    assert payload["sid"] == "s-1"


def test_create_access_token_honors_explicit_expiry() -> None:
    payload = _decode(create_access_token(subject="user@example.com", expires_delta=timedelta(minutes=1)))
    default_payload = _decode(create_access_token(subject="user@example.com"))

    assert payload["exp"] < default_payload["exp"]


def test_every_token_has_a_unique_id() -> None:
    assert _decode(create_access_token("a"))["jti"] != _decode(create_access_token("a"))["jti"]


def test_decode_access_token_rejects_garbage() -> None:
    assert decode_access_token("not-a-jwt-at-all") is None


def test_decode_access_token_rejects_expired_token() -> None:
    token = create_access_token(subject="user@example.com", expires_delta=timedelta(seconds=-1))

    assert decode_access_token(token) is None


def test_decode_access_token_rejects_wrong_signature() -> None:
    settings = get_settings()
    claims = jwt.get_unverified_claims(create_access_token(subject="attacker@example.com"))
    forged = jwt.encode(claims, "a-different-secret", algorithm=ALGORITHM)

    assert decode_access_token(forged) is None
    genuine = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)
    assert decode_access_token(genuine) == "attacker@example.com"


def test_decode_access_token_rejects_tokens_without_issuer_or_audience() -> None:
    settings = get_settings()
    bare = jwt.encode({"sub": "attacker@example.com", "exp": 9999999999}, settings.secret_key, algorithm=ALGORITHM)

    assert decode_access_token(bare) is None


def test_decode_access_token_rejects_foreign_audience() -> None:
    settings = get_settings()
    claims = jwt.get_unverified_claims(create_access_token(subject="u"))
    claims["aud"] = "some-other-service"

    assert decode_access_token(jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)) is None


def test_mfa_challenge_token_is_not_an_access_token() -> None:
    challenge = create_access_token("u", token_type=TOKEN_TYPE_MFA)

    assert decode_access_token(challenge) is None
    assert decode_token_claims(challenge, token_type=TOKEN_TYPE_MFA)["sub"] == "u"


def test_totp_matches_rfc6238_vectors() -> None:
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32("12345678901234567890")

    assert verify_totp(secret, "287082", at=59, window=0)
    assert verify_totp(secret, "081804", at=1111111109, window=0)
    assert not verify_totp(secret, "287083", at=59, window=0)
    assert not verify_totp(secret, "abcdef", at=59)


def test_totp_tolerates_one_step_of_clock_drift_only() -> None:
    secret = generate_totp_secret()
    code_now = _totp_at(secret, 1000)

    assert verify_totp(secret, code_now, at=1000 * 30 + 31)  # next step
    assert not verify_totp(secret, code_now, at=1000 * 30 + 95)  # three steps later


def test_totp_secret_is_encrypted_at_rest() -> None:
    secret = generate_totp_secret()
    stored = encrypt_secret(secret)

    assert secret not in stored
    assert decrypt_secret(stored) == secret
    assert decrypt_secret("not-a-valid-token") is None


def test_password_policy() -> None:
    assert password_policy_errors("Corta1!") != []
    assert password_policy_errors("sinmayusculas123!") != []
    assert password_policy_errors("SinNumeros!!Largo") != []
    assert password_policy_errors("SinSimbolos12345") != []
    assert password_policy_errors("jane.Doe#2026xyz", email="jane.doe@example.com") != []
    assert password_policy_errors("Licitaciones#2026!") == []


def test_refresh_tokens_are_random_and_stored_hashed() -> None:
    token = generate_refresh_token()

    assert token != generate_refresh_token()
    assert len(hash_token(token)) == 64 and token not in hash_token(token)


def test_password_hash_round_trips() -> None:
    hashed = get_password_hash("Sup3rSecret!")

    assert verify_password("Sup3rSecret!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_password_hash_is_salted() -> None:
    first = get_password_hash("same-password")
    second = get_password_hash("same-password")

    assert first != second
    assert verify_password("same-password", first)
    assert verify_password("same-password", second)
