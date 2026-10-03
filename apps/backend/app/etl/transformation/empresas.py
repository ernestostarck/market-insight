from __future__ import annotations

from typing import Any

from app.etl.transformation.base import BaseRecordTransformer, _iso_datetime


class EmpresasTransformer(BaseRecordTransformer):
    """Transforms a normalized empresa into an analytical payload."""

    entity = "empresa"

    def to_analytical_payload(
        self, normalized_payload: dict[str, object]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "external_id": normalized_payload.get("external_id"),
            "rut": normalized_payload.get("rut"),
            "name": normalized_payload.get("name"),
            "legal_name": normalized_payload.get("legal_name"),
            "company_type": normalized_payload.get("company_type"),
            "status": normalized_payload.get("status"),
            "updated_at": _iso_datetime(normalized_payload.get("updated_at")),
        }
        return {key: value for key, value in payload.items() if value is not None}
