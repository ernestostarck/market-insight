from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


def payload_hash(payload: dict[str, Any] | list[Any]) -> str:
    """Return a stable SHA-256 hex digest for a payload.

    Uses deterministic JSON serialization (sort_keys=True) so equal logical
    payloads produce identical hashes regardless of key ordering. This is the
    basis for the deduplication step (Fase 3.8): exact duplicates produce the
    same hash, while data updates change the digest.
    """
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_json.encode("utf-8")).hexdigest()
