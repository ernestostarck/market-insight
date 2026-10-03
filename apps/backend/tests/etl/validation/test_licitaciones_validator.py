from datetime import datetime, timezone

from app.etl.models import StoredRawRecord
from app.etl.validation.validators import LicitacionesRawValidator


def test_licitaciones_validator_normalizes_valid_payload() -> None:
    validator = LicitacionesRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="licitaciones",
            source_id="1000-1-LR26",
            payload={
                "CodigoExterno": "1000-1-LR26",
                "Nombre": "Compra de prueba",
                "Estado": "adjudicada",
                "FechaPublicacion": "2026-08-06",
                "FechaCierre": "2026-08-20",
                "CodigoOrganismo": "7001",
                "NombreOrganismo": "Servicio de Salud",
            },
            payload_hash="a" * 64,
            received_at=datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-1",
        )
    )

    assert result.is_valid is True
    assert result.issues == []
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "1000-1-LR26"
    assert result.normalized_payload["status"] == "ADJUDICADA"
    assert result.normalized_payload["agency_code"] == "7001"


def test_licitaciones_validator_rejects_missing_codigo_externo() -> None:
    validator = LicitacionesRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="licitaciones",
            source_id="missing-code",
            payload={"Estado": "PUBLICADA"},
            payload_hash="b" * 64,
            received_at=datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-2",
        )
    )

    assert result.is_valid is False
    assert result.normalized_payload is None
    assert result.issues[0].field == "CodigoExterno"


def test_licitaciones_validator_rejects_invalid_date() -> None:
    validator = LicitacionesRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="licitaciones",
            source_id="1000-1-LR26",
            payload={
                "CodigoExterno": "1000-1-LR26",
                "Estado": "PUBLICADA",
                "FechaPublicacion": "2026/99/99",
            },
            payload_hash="c" * 64,
            received_at=datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-3",
        )
    )

    assert result.is_valid is False
    assert result.normalized_payload is None
    assert result.issues[0].code == "invalid_date"
    assert result.issues[0].field == "FechaPublicacion"


def test_licitaciones_validator_rejects_unsupported_resource() -> None:
    validator = LicitacionesRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="ordenes_compra",
            source_id="1000-1-LR26",
            payload={"CodigoExterno": "1000-1-LR26", "Estado": "PUBLICADA"},
            payload_hash="d" * 64,
            received_at=datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-4",
        )
    )

    assert result.is_valid is False
    assert result.normalized_payload is None
    assert result.issues[0].code == "unsupported_resource"
