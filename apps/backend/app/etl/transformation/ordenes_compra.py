from __future__ import annotations

from typing import Any

from app.etl.transformation.base import BaseRecordTransformer, _iso_datetime


class OrdenesCompraTransformer(BaseRecordTransformer):
    """Transforms a normalized orden de compra into an analytical payload."""

    entity = "orden_compra"

    def to_analytical_payload(
        self, normalized_payload: dict[str, object]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "external_id": normalized_payload.get("external_id"),
            "title": normalized_payload.get("title"),
            "status": normalized_payload.get("status"),
            "created_at": _iso_datetime(normalized_payload.get("created_at")),
            "issued_at": _iso_datetime(normalized_payload.get("issued_at")),
            "provider_code": normalized_payload.get("provider_code"),
            "provider_name": normalized_payload.get("provider_name"),
            "agency_code": normalized_payload.get("agency_code"),
            "agency_name": normalized_payload.get("agency_name"),
            "total_amount": normalized_payload.get("total_amount"),
        }
        return {key: value for key, value in payload.items() if value is not None}
