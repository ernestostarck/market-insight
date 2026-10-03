from __future__ import annotations

from typing import Any

from app.etl.transformation.base import BaseRecordTransformer, _iso_datetime


class AdjudicacionesTransformer(BaseRecordTransformer):
    """Transforms a normalized adjudicacion into an analytical payload."""

    entity = "adjudicacion"

    def to_analytical_payload(
        self, normalized_payload: dict[str, object]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "external_id": normalized_payload.get("external_id"),
            "title": normalized_payload.get("title"),
            "status": normalized_payload.get("status"),
            "published_at": _iso_datetime(normalized_payload.get("published_at")),
            "awarded_at": _iso_datetime(normalized_payload.get("awarded_at")),
            "agency_code": normalized_payload.get("agency_code"),
            "agency_name": normalized_payload.get("agency_name"),
            "provider_code": normalized_payload.get("provider_code"),
            "provider_name": normalized_payload.get("provider_name"),
            "awarded_amount": normalized_payload.get("awarded_amount"),
            "estimated_amount": normalized_payload.get("estimated_amount"),
            "award_ratio": normalized_payload.get("award_ratio"),
            "offers_count": normalized_payload.get("offers_count"),
            "quality_flags": normalized_payload.get("quality_flags"),
        }
        return {key: value for key, value in payload.items() if value is not None}
