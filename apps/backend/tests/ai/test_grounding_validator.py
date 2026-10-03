"""Unit tests for FactualGroundingValidator (Fase 9.15)."""

import pytest

from app.ai.contracts import Context, Source
from app.ai.grounding_validator import (
    INSUFFICIENT_EVIDENCE_FALLBACK,
    FactualGroundingValidator,
)


@pytest.mark.asyncio
async def test_grounding_validator_passes_verified_claims():
    validator = FactualGroundingValidator(min_grounding_score=0.80)

    context = Context(
        formatted_prompt_context=(
            "### CONTEXT - UNTRUSTED DATA BEGIN ###\n"
            "[Fuente: licitacion 1234-56-LP24] Adquisición por $45.000.000 CLP en el año 2024 "
            "para el proveedor RUT 76.123.456-7.\n"
            "### CONTEXT - UNTRUSTED DATA END ###"
        ),
        sources=[
            Source(
                id="1234-56-LP24",
                source_type="tender",
                title="Licitación 2024",
                snippet="Adquisición por $45.000.000 CLP",
            )
        ],
    )

    answer = (
        "En la licitación 1234-56-LP24 se adjudicaron $45.000.000 CLP durante el año 2024 "
        "al proveedor RUT 76.123.456-7."
    )

    result = await validator.validate(answer, context)

    assert result.is_grounded is True
    assert result.grounding_score == 1.0
    assert result.unsupported_claims == []
    assert len(result.validated_sources) >= 1


@pytest.mark.asyncio
async def test_grounding_validator_flags_unsupported_hallucinations():
    validator = FactualGroundingValidator(min_grounding_score=0.80)

    context = Context(
        formatted_prompt_context="El presupuesto total fue de $10.000.000 CLP.",
        sources=[],
    )

    # Hallucinates a different amount $99.000.000 CLP, a fake RUT, and a fake code
    answer = (
        "El monto ascendió a $99.000.000 CLP para el RUT 99.888.777-K bajo la licitación 9999-99-LR24."
    )

    result = await validator.validate(answer, context)

    assert result.is_grounded is False
    assert result.grounding_score < 0.50
    assert len(result.unsupported_claims) >= 2


@pytest.mark.asyncio
async def test_grounding_validator_recognizes_transparent_refusal():
    validator = FactualGroundingValidator()

    context = Context(
        formatted_prompt_context="No se encontraron registros.",
        sources=[],
    )

    answer = "No encontré evidencia suficiente en los datos disponibles para responder sobre este proveedor."
    result = await validator.validate(answer, context)

    assert result.is_grounded is True
    assert result.grounding_score == 1.0


def test_enforce_grounding_substitutes_failed_answer():
    validator = FactualGroundingValidator(grounding_required=True)

    fake_answer = "Cifras inventadas por $888.000.000 CLP."
    from app.ai.contracts import GroundingResult

    failed_result = GroundingResult(
        is_grounded=False,
        grounding_score=0.2,
        unsupported_claims=["$888.000.000 CLP"],
    )

    enforced = validator.enforce_grounding(fake_answer, failed_result)
    assert enforced == INSUFFICIENT_EVIDENCE_FALLBACK


def test_extract_factual_claims_variety():
    validator = FactualGroundingValidator()
    text = (
        "La orden 123-45-CM24 por $15.500.000 CLP con RUT 12.345.678-9 en 2023 "
        "y otra licitación 987-65-LP22 por 50.000 USD."
    )

    claims = validator.extract_factual_claims(text)
    assert "123-45-CM24" in claims
    assert "987-65-LP22" in claims
    assert "12.345.678-9" in claims
    assert "2023" in claims
