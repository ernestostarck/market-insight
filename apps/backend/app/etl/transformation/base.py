from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol

from app.etl.models import TransformedRecord
from app.etl.transformation.hashing import payload_hash
from app.etl.transformation.keys import natural_key


class RecordTransformer(Protocol):
    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord: ...


class BaseRecordTransformer(ABC):
    """Common machinery shared by all entity transformers.

    Subclasses implement :meth:`to_entity` returning the analytical payload to
    persist; this base builds the ``natural_key`` and computes the
    ``payload_hash`` used by the deduplication step.
    """

    entity: str
    source: str = "chilecompra"

    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord:
        external_id = self._external_id(normalized_payload)
        analytical_payload = self.to_analytical_payload(normalized_payload)
        return TransformedRecord(
            entity=self.entity,
            natural_key=natural_key(
                self.entity,
                external_id,
                source=self.source,
            ),
            payload=analytical_payload,
            source_id=external_id,
            payload_hash=payload_hash(analytical_payload),
        )

    @abstractmethod
    def to_analytical_payload(
        self, normalized_payload: dict[str, object]
    ) -> dict[str, Any]:
        """Return a JSON-serializable analytical payload to load."""

    def _external_id(self, normalized_payload: dict[str, object]) -> str:
        value = normalized_payload.get("external_id")
        return str(value) if value not in (None, "") else "unknown"


def _iso_datetime(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)
