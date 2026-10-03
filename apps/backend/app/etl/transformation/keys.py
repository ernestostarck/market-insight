from __future__ import annotations

_ENTITY_PREFIX = {
    "licitacion": "licitacion",
    "orden_compra": "orden_compra",
    "empresa": "empresa",
    "contrato": "contrato",
    "convenio_marco": "convenio_marco",
    "adjudicacion": "adjudicacion",
    "categoria": "categoria",
}


def natural_key(entity: str, source_id: str, *, source: str = "chilecompra") -> str:
    """Build a stable natural key for a transformed record.

    Format: ``<source>:<entity>:<source_id>``.

    This identifier is used by the deduplication step (Fase 3.8) to determine
    whether a record already exists and if it changed.
    """
    prefix = _ENTITY_PREFIX.get(entity, entity)
    id_value = str(source_id).strip()
    return f"{source}:{prefix}:{id_value}"
