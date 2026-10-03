from __future__ import annotations

from typing import Any

from app.etl.transformation.base import BaseRecordTransformer, _iso_datetime


class LicitacionesTransformer(BaseRecordTransformer):
    """Transforms a normalized licitacion into an analytical payload."""

    entity = "licitacion"

    def to_analytical_payload(
        self, normalized_payload: dict[str, object]
    ) -> dict[str, Any]:
        # Field names match core.licitacion columns (app/models/core/licitacion.py),
        # the Alembic-migrated canonical table — not the legacy procurement.licitaciones
        # names (title/status) that app/etl/loading/mapping.py still uses for the
        # unwired PostgresRecordLoader/BulkCopyLoader.
        payload: dict[str, Any] = {
            "codigo": normalized_payload.get("external_id"),
            "nombre": normalized_payload.get("title"),
            "estado": normalized_payload.get("status"),
            "fecha_publicacion": _iso_datetime(normalized_payload.get("published_at")),
            "fecha_cierre": _iso_datetime(normalized_payload.get("closing_at")),
            "agency_code": normalized_payload.get("agency_code"),
            "agency_name": normalized_payload.get("agency_name"),
        }
        return {key: value for key, value in payload.items() if value is not None}
