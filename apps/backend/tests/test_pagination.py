from __future__ import annotations

import pytest

from app.core.pagination import decode_cursor, encode_cursor


def test_cursor_is_signed_and_resource_scoped() -> None:
    token = encode_cursor("licitaciones", 42, "next")
    cursor = decode_cursor(token, "licitaciones")
    assert cursor.anchor_id == 42
    assert cursor.direction == "next"

    with pytest.raises(ValueError, match="resource"):
        decode_cursor(token, "proveedores")


def test_cursor_rejects_tampering() -> None:
    token = encode_cursor("licitaciones", 42, "next")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(ValueError, match="cursor"):
        decode_cursor(tampered, "licitaciones")


def test_cursor_round_trips_regardless_of_signature_byte_content() -> None:
    # Regression test: the signature is raw HMAC-SHA256 output and has roughly
    # a 12% chance per token of containing a 0x2e ('.') byte. Segments must be
    # base64url-encoded *before* being joined with "." (JWT-style), or that
    # byte corrupts the payload/signature split and a valid cursor spuriously
    # fails to decode.
    for anchor_id in range(1, 500):
        token = encode_cursor("licitaciones", anchor_id, "next")
        cursor = decode_cursor(token, "licitaciones")
        assert cursor.anchor_id == anchor_id
        assert cursor.direction == "next"
