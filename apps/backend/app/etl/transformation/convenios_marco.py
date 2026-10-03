from __future__ import annotations

from typing import Any

from app.etl.transformation.base import BaseRecordTransformer, _iso_datetime


class ConveniosMarcoTransformer(BaseRecordTransformer):
    """Transforms a normalized convenio marco into an analytical payload."""

    entity = "convenio_marco"

    def to_analytical_payload(
        self, normalized_payload: dict[str, object]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "external_id": normalized_payload.get("external_id"),
            "title": normalized_payload.get("title"),
            "status": normalized_payload.get("status"),
            "created_at": _iso_datetime(normalized_payload.get("created_at")),
            "start_at": _iso_datetime(normalized_payload.get("start_at")),
            "end_at": _iso_datetime(normalized_payload.get("end_at")),
            "agency_code": normalized_payload.get("agency_code"),
            "agency_name": normalized_payload.get("agency_name"),
            "total_amount": normalized_payload.get("total_amount"),
        }
        return {key: value for key, value in payload.items() if value is not None}
