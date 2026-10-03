from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Callable

from pydantic import ValidationError

from app.etl.models import StoredRawRecord, ValidationIssue, ValidationResult
from app.etl.validation.base import RecordValidator
from app.integrations.chilecompra.exceptions import (
    ChileCompraValidationError as _ChileCompraValidationError,
)
from app.integrations.chilecompra.models import (
    AdjudicacionAPIItem,
    ContratoAPIItem,
    ConvenioMarcoAPIItem,
    EmpresaAPIItem,
    LicitacionAPIItem,
    OrdenCompraAPIItem,
)
from app.integrations.chilecompra.parsers.adjudicaciones import (
    normalize_adjudicaciones,
)
from app.integrations.chilecompra.parsers.contratos import normalize_contratos
from app.integrations.chilecompra.parsers.convenios_marco import (
    normalize_convenios_marco,
)
from app.integrations.chilecompra.parsers.empresas import normalize_empresas
from app.integrations.chilecompra.parsers.licitaciones import normalize_licitaciones
from app.integrations.chilecompra.parsers.ordenes_compra import (
    normalize_ordenes_compra,
)

_LICITACIONES_DATE_FIELDS = {
    "FechaPublicacion": "published_at",
    "FechaCierre": "closing_at",
}
_ORDENES_COMPRA_DATE_FIELDS = {
    "FechaCreacion": "created_at",
    "FechaEmision": "issued_at",
}
_EMPRESAS_DATE_FIELDS = {
    "FechaActualizacion": "updated_at",
}
_CONTRATOS_DATE_FIELDS = {
    "FechaCreacion": "created_at",
    "FechaInicio": "start_at",
    "FechaFin": "end_at",
}
_CONVENIOS_MARCO_DATE_FIELDS = {
    "FechaCreacion": "created_at",
    "FechaInicio": "start_at",
    "FechaFin": "end_at",
}
_ADJUDICACIONES_DATE_FIELDS = {
    "FechaPublicacion": "published_at",
    "FechaAdjudicacion": "awarded_at",
}


class _ResourceRawValidator(RecordValidator):
    schema_model: type
    normalize_payload: Callable[[dict[str, Any] | list[Any]], list[Any]]
    supported_resources: set[str]
    date_fields: dict[str, str]
    resource_label: str

    def validate(self, record: StoredRawRecord) -> ValidationResult:
        if record.resource not in self.supported_resources:
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="unsupported_resource",
                        message=(
                            f"Unsupported resource for {self.resource_label} validation: {record.resource}"
                        ),
                        field="resource",
                    )
                ],
            )

        try:
            self.schema_model.model_validate(record.payload)
        except ValidationError as exc:
            return ValidationResult(
                is_valid=False,
                issues=_validation_issues_from_pydantic(exc),
            )

        try:
            normalized = self.normalize_payload([record.payload])[0]
        except _ChileCompraValidationError as exc:
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="normalization_error",
                        message=str(exc),
                        field=None,
                    )
                ],
            )

        normalized_payload = normalized.model_dump()
        issues = _date_issues(record.payload, normalized_payload, self.date_fields)
        if issues:
            return ValidationResult(is_valid=False, issues=issues)

        return ValidationResult(is_valid=True, normalized_payload=normalized_payload)


class LicitacionesRawValidator(_ResourceRawValidator):
    """Schema validation and normalization for raw licitaciones payloads."""

    def __init__(
        self,
        *,
        supported_resources: Iterable[str] | None = None,
    ) -> None:
        self.schema_model = LicitacionAPIItem
        self.normalize_payload = normalize_licitaciones
        self.supported_resources = set(
            supported_resources or {"licitaciones", "licitaciones_historicas"}
        )
        self.date_fields = _LICITACIONES_DATE_FIELDS
        self.resource_label = "licitaciones"


class OrdenesCompraRawValidator(_ResourceRawValidator):
    """Schema validation and normalization for raw ordenes_compra payloads."""

    def __init__(
        self,
        *,
        supported_resources: Iterable[str] | None = None,
    ) -> None:
        self.schema_model = OrdenCompraAPIItem
        self.normalize_payload = normalize_ordenes_compra
        self.supported_resources = set(
            supported_resources or {"ordenes_compra", "ordenes_compra_historicas"}
        )
        self.date_fields = _ORDENES_COMPRA_DATE_FIELDS
        self.resource_label = "ordenes_compra"


class EmpresasRawValidator(_ResourceRawValidator):
    """Schema validation and normalization for raw empresas payloads."""

    def __init__(
        self,
        *,
        supported_resources: Iterable[str] | None = None,
    ) -> None:
        self.schema_model = EmpresaAPIItem
        self.normalize_payload = normalize_empresas
        self.supported_resources = set(
            supported_resources or {"empresas", "proveedores", "empresas_historicas"}
        )
        self.date_fields = _EMPRESAS_DATE_FIELDS
        self.resource_label = "empresas"


class ContratosRawValidator(_ResourceRawValidator):
    """Schema validation and normalization for raw contratos payloads."""

    def __init__(
        self,
        *,
        supported_resources: Iterable[str] | None = None,
    ) -> None:
        self.schema_model = ContratoAPIItem
        self.normalize_payload = normalize_contratos
        self.supported_resources = set(
            supported_resources or {"contratos", "contratos_historicas"}
        )
        self.date_fields = _CONTRATOS_DATE_FIELDS
        self.resource_label = "contratos"


class ConveniosMarcoRawValidator(_ResourceRawValidator):
    """Schema validation and normalization for raw convenios_marco payloads."""

    def __init__(
        self,
        *,
        supported_resources: Iterable[str] | None = None,
    ) -> None:
        self.schema_model = ConvenioMarcoAPIItem
        self.normalize_payload = normalize_convenios_marco
        self.supported_resources = set(
            supported_resources or {"convenios_marco", "convenios_marco_historicas"}
        )
        self.date_fields = _CONVENIOS_MARCO_DATE_FIELDS
        self.resource_label = "convenios_marco"


class AdjudicacionesRawValidator(_ResourceRawValidator):
    """Schema validation and normalization for raw adjudicaciones payloads."""

    def __init__(
        self,
        *,
        supported_resources: Iterable[str] | None = None,
    ) -> None:
        self.schema_model = AdjudicacionAPIItem
        self.normalize_payload = normalize_adjudicaciones
        self.supported_resources = set(
            supported_resources or {"adjudicaciones", "adjudicaciones_historicas"}
        )
        self.date_fields = _ADJUDICACIONES_DATE_FIELDS
        self.resource_label = "adjudicaciones"


class ResourceValidationRouter(RecordValidator):
    """Dispatch validation by ETL resource name for heterogeneous raw streams."""

    def __init__(self, validators_by_resource: Mapping[str, RecordValidator]) -> None:
        self._validators_by_resource = dict(validators_by_resource)

    def validate(self, record: StoredRawRecord) -> ValidationResult:
        validator = self._validators_by_resource.get(record.resource)
        if validator is None:
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="validator_not_found",
                        message=f"No validator registered for resource: {record.resource}",
                        field="resource",
                    )
                ],
            )
        return validator.validate(record)


def default_validation_router() -> ResourceValidationRouter:
    licitaciones = LicitacionesRawValidator()
    ordenes = OrdenesCompraRawValidator()
    empresas = EmpresasRawValidator()
    contratos = ContratosRawValidator()
    convenios = ConveniosMarcoRawValidator()
    adjudicaciones = AdjudicacionesRawValidator()
    return ResourceValidationRouter(
        {
            resource: licitaciones
            for resource in {"licitaciones", "licitaciones_historicas"}
        }
        | {
            resource: ordenes
            for resource in {"ordenes_compra", "ordenes_compra_historicas"}
        }
        | {
            resource: empresas
            for resource in {"empresas", "proveedores", "empresas_historicas"}
        }
        | {resource: contratos for resource in {"contratos", "contratos_historicas"}}
        | {
            resource: convenios
            for resource in {"convenios_marco", "convenios_marco_historicas"}
        }
        | {
            resource: adjudicaciones
            for resource in {"adjudicaciones", "adjudicaciones_historicas"}
        }
    )


def _validation_issues_from_pydantic(exc: ValidationError) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for error in exc.errors():
        path = ".".join(str(part) for part in error.get("loc", [])) or None
        issues.append(
            ValidationIssue(
                code=str(error.get("type", "validation_error")),
                message=str(error.get("msg", "Invalid payload")),
                field=path,
            )
        )
    return issues


def _date_issues(
    raw_payload: dict[str, object],
    normalized_payload: dict[str, object],
    date_fields: dict[str, str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for raw_field, normalized_field in date_fields.items():
        raw_value = raw_payload.get(raw_field)
        normalized_value = normalized_payload.get(normalized_field)
        if raw_value and normalized_value is None:
            issues.append(
                ValidationIssue(
                    code="invalid_date",
                    message=f"Invalid date value for {raw_field}",
                    field=raw_field,
                )
            )
    return issues
