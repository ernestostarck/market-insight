from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TableMapping:
    """Describes where a transformed entity is persisted."""

    schema: str
    table: str
    natural_key_column: str = "natural_key"
    payload_hash_column: str = "payload_hash"
    # payload field -> SQL column name
    columns: dict[str, str] = field(default_factory=dict)


# Entity -> target table mapping. The SQL columns come from docker/postgres/
# init/003-schema.sql (procurement.*). Unless specified here, a payload field is
# ignored. ``external_id`` maps to the physical ``external_id`` column.
_ENTITY_TABLES: dict[str, TableMapping] = {
    "licitacion": TableMapping(
        schema="procurement",
        table="licitaciones",
        columns={
            "external_id": "external_id",
            "title": "title",
            "status": "status",
            "published_at": "published_at",
            "closing_at": "closing_at",
            "agency_code": "agency_code",
            "agency_name": "agency_name",
            "source": "source",
        },
    ),
    "orden_compra": TableMapping(
        schema="procurement",
        table="ordenes_compra",
        columns={
            "external_id": "external_id",
            "title": "title",
            "status": "status",
            "created_at": "created_at",
            "issued_at": "issued_at",
            "provider_code": "provider_code",
            "provider_name": "provider_name",
            "agency_code": "agency_code",
            "agency_name": "agency_name",
            "total_amount": "total_amount",
            "source": "source",
        },
    ),
    "empresa": TableMapping(
        schema="procurement",
        table="proveedores",
        columns={
            "external_id": "external_id",
            "rut": "rut",
            "name": "name",
            "legal_name": "legal_name",
            "company_type": "company_type",
            "status": "status",
            "updated_at": "updated_at",
            "source": "source",
        },
    ),
    "contrato": TableMapping(
        schema="procurement",
        table="contratos",
        columns={
            "external_id": "external_id",
            "title": "title",
            "status": "status",
            "created_at": "created_at",
            "start_at": "start_at",
            "end_at": "end_at",
            "provider_code": "provider_code",
            "provider_name": "provider_name",
            "agency_code": "agency_code",
            "agency_name": "agency_name",
            "total_amount": "total_amount",
            "source": "source",
        },
    ),
    "convenio_marco": TableMapping(
        schema="procurement",
        table="convenios_marco",
        columns={
            "external_id": "external_id",
            "title": "title",
            "status": "status",
            "created_at": "created_at",
            "start_at": "start_at",
            "end_at": "end_at",
            "agency_code": "agency_code",
            "agency_name": "agency_name",
            "total_amount": "total_amount",
            "source": "source",
        },
    ),
    "adjudicacion": TableMapping(
        schema="procurement",
        table="adjudicaciones",
        columns={
            "external_id": "external_id",
            "title": "title",
            "status": "status",
            "published_at": "published_at",
            "awarded_at": "awarded_at",
            "agency_code": "agency_code",
            "agency_name": "agency_name",
            "provider_code": "provider_code",
            "provider_name": "provider_name",
            "awarded_amount": "awarded_amount",
            "estimated_amount": "estimated_amount",
            "award_ratio": "award_ratio",
            "offers_count": "offers_count",
            "quality_flags": "quality_flags",
            "source": "source",
        },
    ),
}


def table_for(entity: str) -> TableMapping:
    """Return the target TableMapping for an entity.

    Raises KeyError when the entity is not a known analytical entity.
    """
    return _ENTITY_TABLES[entity]


def has_table(entity: str) -> bool:
    """Whether entity maps to a persisted table."""
    return entity in _ENTITY_TABLES


def table_name(entity: str, *, qualified: bool = True) -> str:
    mapping = table_for(entity)
    if qualified:
        return f"{mapping.schema}.{mapping.table}"
    return mapping.table


def project_columns(
    mapping: TableMapping,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Return only the payload fields that map to physical columns.

    ``None`` values are dropped to let the DB defaults apply where possible.
    """
    projected: dict[str, Any] = {}
    for payload_key, column in mapping.columns.items():
        if payload_key not in payload:
            continue
        value = payload[payload_key]
        if value is None:
            continue
        projected[column] = value
    return projected
