"""Opaque, signed cursor encoding for keyset pagination."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal

from app.core.settings import get_settings

CursorDirection = Literal["next", "previous"]


@dataclass(frozen=True, slots=True)
class Cursor:
    resource: str
    anchor_id: int
    direction: CursorDirection


def encode_cursor(resource: str, anchor_id: int, direction: CursorDirection) -> str:
    payload = json.dumps(
        {"r": resource, "i": anchor_id, "d": direction},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    signature = hmac.new(_secret(), payload, hashlib.sha256).digest()
    # Segments are base64url-encoded *before* joining (JWT-style): that alphabet
    # never contains ".", so splitting on it below is unambiguous. Joining the
    # raw binary payload/signature with a literal b"." first and encoding the
    # whole blob together was buggy - the signature is random bytes and has a
    # ~12% chance of containing a 0x2e ('.') byte itself, corrupting the split.
    return f"{_encode(payload)}.{_encode(signature)}"


def decode_cursor(token: str, resource: str) -> Cursor:
    try:
        encoded_payload, encoded_signature = token.rsplit(".", 1)
        payload = _decode(encoded_payload)
        signature = _decode(encoded_signature)
        expected = hmac.new(_secret(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid cursor signature")
        data = json.loads(payload)
        cursor = Cursor(
            resource=str(data["r"]),
            anchor_id=int(data["i"]),
            direction=data["d"],
        )
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid pagination cursor") from exc
    if cursor.resource != resource:
        raise ValueError("cursor does not belong to this resource")
    if cursor.anchor_id < 1 or cursor.direction not in {"next", "previous"}:
        raise ValueError("invalid pagination cursor")
    return cursor


def _secret() -> bytes:
    return get_settings().secret_key.encode()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
