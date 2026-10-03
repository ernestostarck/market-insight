from datetime import datetime, timezone

from app.etl.models import StoredRawRecord
from app.etl.validation.validators import (
    AdjudicacionesRawValidator,
    ContratosRawValidator,
    ConveniosMarcoRawValidator,
    default_validation_router,
)


def _make_record(
    resource: str,
    source_id: str,
    payload: dict,
    *,
    run_id: str = "run-adv-1",
) -> StoredRawRecord:
    return StoredRawRecord(
        source="chilecompra_api",
        resource=resource,
        source_id=source_id,
        payload=payload,
        payload_hash="r" * 64,
        received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
        ingestion_run_id=run_id,
    )


class TestContratosRawValidator:
    def test_normalizes_valid_payload(self) -> None:
        validator = ContratosRawValidator()
        result = validator.validate(
            _make_record(
                resource="contratos",
                source_id="2580-300-LR26",
                payload={
                    "CodigoContrato": "2580-300-LR26",
                    "Nombre": "Contrato de soporte clinico",
                    "Estado": "vigente",
                    "FechaCreacion": "2026-08-06",
                    "FechaInicio": "2026-08-07",
                    "FechaFin": "2027-08-07",
                    "CodigoProveedor": "76123456-7",
                    "NombreProveedor": "Proveedor Demo SPA",
                    "CodigoOrganismo": "701",
                    "NombreOrganismo": "Servicio Nacional",
                    "MontoTotal": 8500000,
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        assert result.normalized_payload["external_id"] == "2580-300-LR26"
        assert result.normalized_payload["status"] == "VIGENTE"
        assert result.normalized_payload["provider_code"] == "76123456-7"
        assert result.normalized_payload["agency_code"] == "701"
        assert result.normalized_payload["total_amount"] == 8500000

    def test_rejects_invalid_date(self) -> None:
        validator = ContratosRawValidator()
        result = validator.validate(
            _make_record(
                resource="contratos",
                source_id="2580-300-LR26",
                payload={
                    "CodigoContrato": "2580-300-LR26",
                    "Estado": "VIGENTE",
                    "FechaInicio": "2026/99/99",
                },
            )
        )

        assert result.is_valid is False
        assert result.normalized_payload is None
        assert result.issues[0].code == "invalid_date"
        assert result.issues[0].field == "FechaInicio"

    def test_rejects_unsupported_resource(self) -> None:
        validator = ContratosRawValidator()
        result = validator.validate(
            _make_record(
                resource="empresas",
                source_id="EMP-1",
                payload={"CodigoContrato": "2580-300-LR26", "Estado": "VIGENTE"},
            )
        )

        assert result.is_valid is False
        assert result.issues[0].code == "unsupported_resource"


class TestConveniosMarcoRawValidator:
    def test_normalizes_valid_payload(self) -> None:
        validator = ConveniosMarcoRawValidator()
        result = validator.validate(
            _make_record(
                resource="convenios_marco",
                source_id="2239-17-LR26",
                payload={
                    "CodigoConvenio": "2239-17-LR26",
                    "Nombre": "Convenio de equipamiento asistencial",
                    "Estado": "vigente",
                    "FechaCreacion": "2026-08-06",
                    "FechaInicio": "2026-08-07",
                    "FechaFin": "2027-08-07",
                    "CodigoOrganismo": "701",
                    "NombreOrganismo": "Servicio Nacional",
                    "MontoTotal": 19000000,
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        assert result.normalized_payload["external_id"] == "2239-17-LR26"
        assert result.normalized_payload["status"] == "VIGENTE"
        assert result.normalized_payload["agency_code"] == "701"
        assert result.normalized_payload["total_amount"] == 19000000

    def test_rejects_invalid_date(self) -> None:
        validator = ConveniosMarcoRawValidator()
        result = validator.validate(
            _make_record(
                resource="convenios_marco",
                source_id="2239-17-LR26",
                payload={
                    "CodigoConvenio": "2239-17-LR26",
                    "Estado": "VIGENTE",
                    "FechaFin": "no-date",
                },
            )
        )

        assert result.is_valid is False
        assert result.issues[0].code == "invalid_date"
        assert result.issues[0].field == "FechaFin"


class TestAdjudicacionesRawValidator:
    def test_normalizes_valid_payload(self) -> None:
        validator = AdjudicacionesRawValidator()
        result = validator.validate(
            _make_record(
                resource="adjudicaciones",
                source_id="1000-44-LR26",
                payload={
                    "CodigoAdjudicacion": "1000-44-LR26",
                    "Nombre": "Adjudicacion de equipos clinicos",
                    "Estado": "adjudicada",
                    "FechaPublicacion": "2026-08-06",
                    "FechaAdjudicacion": "2026-08-12",
                    "CodigoOrganismo": "701",
                    "NombreOrganismo": "Servicio Nacional",
                    "CodigoProveedor": "76123456-7",
                    "NombreProveedor": "Proveedor Demo SPA",
                    "MontoAdjudicado": "1500000",
                    "MontoEstimado": "2000000",
                    "CantidadOfertas": "6",
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        assert result.normalized_payload["external_id"] == "1000-44-LR26"
        assert result.normalized_payload["status"] == "ADJUDICADA"
        assert result.normalized_payload["provider_code"] == "76123456-7"
        assert result.normalized_payload["awarded_amount"] == 1500000
        assert result.normalized_payload["award_ratio"] == 0.75

    def test_rejects_invalid_date(self) -> None:
        validator = AdjudicacionesRawValidator()
        result = validator.validate(
            _make_record(
                resource="adjudicaciones",
                source_id="1000-44-LR26",
                payload={
                    "CodigoAdjudicacion": "1000-44-LR26",
                    "Estado": "ADJUDICADA",
                    "FechaAdjudicacion": "2026-13-40",
                },
            )
        )

        assert result.is_valid is False
        assert result.issues[0].code == "invalid_date"
        assert result.issues[0].field == "FechaAdjudicacion"

    def test_normalizes_valid_payload_with_fallback_quality_flags(self) -> None:
        validator = AdjudicacionesRawValidator()
        result = validator.validate(
            _make_record(
                resource="adjudicaciones",
                source_id="1000-44-LR26",
                payload={
                    "CodigoAdjudicacion": "1000-44-LR26",
                    "Estado": "adjudicada",
                    "FechaPublicacion": "2026-08-06",
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        quality_flags = result.normalized_payload.get("quality_flags", [])
        assert "missing_awarded_amount" in quality_flags
        assert "missing_estimated_amount" in quality_flags
        assert "missing_offers_count" in quality_flags
        assert "missing_title" in quality_flags


class TestDefaultRouterIncludesNewResources:
    def test_router_dispatches_contratos(self) -> None:
        router = default_validation_router()
        result = router.validate(
            _make_record(
                resource="contratos",
                source_id="2580-300-LR26",
                payload={
                    "CodigoContrato": "2580-300-LR26",
                    "Estado": "VIGENTE",
                    "FechaInicio": "2026-08-07",
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        assert result.normalized_payload["external_id"] == "2580-300-LR26"

    def test_router_dispatches_convenios_marco(self) -> None:
        router = default_validation_router()
        result = router.validate(
            _make_record(
                resource="convenios_marco",
                source_id="2239-17-LR26",
                payload={
                    "CodigoConvenio": "2239-17-LR26",
                    "Estado": "VIGENTE",
                    "FechaInicio": "2026-08-07",
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        assert result.normalized_payload["external_id"] == "2239-17-LR26"

    def test_router_dispatches_adjudicaciones_historicas(self) -> None:
        router = default_validation_router()
        result = router.validate(
            _make_record(
                resource="adjudicaciones_historicas",
                source_id="1000-44-LR26",
                payload={
                    "CodigoAdjudicacion": "1000-44-LR26",
                    "Estado": "ADJUDICADA",
                    "FechaPublicacion": "2026-08-06",
                },
            )
        )

        assert result.is_valid is True
        assert result.normalized_payload is not None
        assert result.normalized_payload["external_id"] == "1000-44-LR26"
