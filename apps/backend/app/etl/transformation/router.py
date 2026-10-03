from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.etl.models import TransformedRecord
from app.etl.transformation.adjudicaciones import AdjudicacionesTransformer
from app.etl.transformation.base import RecordTransformer
from app.etl.transformation.contratos import ContratosTransformer
from app.etl.transformation.convenios_marco import ConveniosMarcoTransformer
from app.etl.transformation.empresas import EmpresasTransformer
from app.etl.transformation.licitaciones import LicitacionesTransformer
from app.etl.transformation.ordenes_compra import OrdenesCompraTransformer


class TransformationRouter(RecordTransformer):
    """Dispatch transformation to the correct entity transformer.

    Each validated record produces a ``normalized_payload`` following the
    corresponding schema. Because the pipeline invokes a single transformer, the
    router infers the target entity from the set of fields present in the
    payload. Entities are identified by their most distinctive analytical keys.
    """

    def __init__(
        self,
        transformers_by_entity: Mapping[str, RecordTransformer],
        *,
        default_entity: str = "unknown",
    ) -> None:
        self._transformers_by_entity = dict(transformers_by_entity)
        self._default_entity = default_entity

    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord:
        entity = self._infer_entity(normalized_payload)
        transformer = self._transformers_by_entity.get(entity)
        if transformer is None:
            return self._unknown_transformed(normalized_payload, entity)
        return transformer.transform(normalized_payload)

    def _infer_entity(self, normalized_payload: dict[str, object]) -> str:
        keys = set(normalized_payload.keys())
        for entity, required in _ENTITY_SIGNATURES.items():
            if required <= keys:
                return entity
        return self._default_entity

    def _unknown_transformed(
        self, normalized_payload: dict[str, object], entity: str
    ) -> TransformedRecord:
        external_id = normalized_payload.get("external_id")
        from app.etl.transformation.hashing import payload_hash
        from app.etl.transformation.keys import natural_key

        source_id = str(external_id) if external_id not in (None, "") else "unknown"
        analytical_payload = dict(normalized_payload)
        return TransformedRecord(
            entity=entity,
            natural_key=natural_key(entity, source_id),
            payload=analytical_payload,
            source_id=source_id,
            payload_hash=payload_hash(analytical_payload),
        )


# Required fields that uniquely identify each normalized entity.
# Order matters: more specific entities are checked first.
_ENTITY_SIGNATURES: dict[str, set[str]] = {
    # contrato vs convenio_marco: contratos carry provider info
    "contrato": {"provider_code", "start_at", "end_at"},
    "convenio_marco": {"start_at", "end_at"},
    "orden_compra": {"issued_at"},
    "adjudicacion": {"awarded_at", "award_ratio"},
    "licitacion": {"closing_at"},
    "empresa": {"rut"},
}


def default_transformation_router() -> TransformationRouter:
    transformers_by_entity: dict[str, RecordTransformer] = {
        "licitacion": LicitacionesTransformer(),
        "orden_compra": OrdenesCompraTransformer(),
        "empresa": EmpresasTransformer(),
        "contrato": ContratosTransformer(),
        "convenio_marco": ConveniosMarcoTransformer(),
        "adjudicacion": AdjudicacionesTransformer(),
    }
    return TransformationRouter(transformers_by_entity)
