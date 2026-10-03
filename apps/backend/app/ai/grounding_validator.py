"""Factual Grounding Validator for MercadoInsight AI (Fase 9.15).

Verifies that factual claims (amounts, tender codes, RUTs, dates, entities) in generated
answers are strictly backed by retrieved evidence, flags hallucinations, and enforces
grounding constraints.
"""

from __future__ import annotations

import re

from app.ai.contracts import Context, GroundingResult, Source
from app.ai.interfaces import GroundingValidator as GroundingValidatorProtocol

# Regular expressions for factual entity verification
_AMOUNT_REGEX = re.compile(
    r"\$\s*\d{1,3}(?:\.\d{3})+(?:,\d+)?|\b\d{1,3}(?:\.\d{3})+\s*(?:pesos|CLP|UF|USD)\b",
    re.IGNORECASE,
)
_TENDER_CODE_REGEX = re.compile(r"\b\d+-\d+-[A-Za-z0-9]{2,6}\b")
_RUT_REGEX = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b")
_YEAR_REGEX = re.compile(r"\b(19\d{2}|20\d{2})\b")

INSUFFICIENT_EVIDENCE_FALLBACK = (
    "No encontré evidencia suficiente en los datos disponibles de Mercado Público "
    "para responder con certeza sobre los antecedentes consultados."
)


class FactualGroundingValidator(GroundingValidatorProtocol):
    """Audits generated answers for fidelity to retrieved context and absence of hallucination."""

    def __init__(
        self,
        min_grounding_score: float = 0.80,
        grounding_required: bool = True,
    ) -> None:
        self.min_grounding_score = min_grounding_score
        self.grounding_required = grounding_required

    def extract_factual_claims(self, text: str) -> list[str]:
        """Extract verifiable factual tokens (amounts, codes, RUTs, years)."""
        claims: list[str] = []

        # 1. Amounts
        for m in _AMOUNT_REGEX.finditer(text):
            claims.append(m.group(0).strip())

        # 2. Tender / procurement codes
        for m in _TENDER_CODE_REGEX.finditer(text):
            claims.append(m.group(0).strip())

        # 3. RUTs
        for m in _RUT_REGEX.finditer(text):
            claims.append(m.group(0).strip())

        # 4. Years
        for m in _YEAR_REGEX.finditer(text):
            claims.append(m.group(0).strip())

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for c in claims:
            low = c.lower()
            if low not in seen:
                seen.add(low)
                deduped.append(c)
        return deduped

    def _search_in_context(self, claim: str, context: Context) -> bool:
        """Check if a factual claim is present in prompt context text or structured data."""
        # 1. Direct search in formatted prompt text
        if claim.lower() in context.formatted_prompt_context.lower():
            return True

        # Normalized search for numbers without thousands punctuation (e.g. 45000000 vs 45.000.000)
        digits_only = re.sub(r"[^\d]", "", claim)
        if len(digits_only) >= 4 and digits_only in re.sub(r"[^\d]", "", context.formatted_prompt_context):
            return True

        # 2. Search in structured tabular data
        if context.structured_data:
            data_str = str(context.structured_data).lower()
            if claim.lower() in data_str:
                return True
            if len(digits_only) >= 4 and digits_only in re.sub(r"[^\d]", "", data_str):
                return True

        # 3. Search in sources metadata
        for s in context.sources:
            if claim.lower() in s.title.lower() or (s.snippet and claim.lower() in s.snippet.lower()):
                return True

        return False

    async def validate(
        self,
        generated_answer: str,
        context: Context,
    ) -> GroundingResult:
        """Evaluate whether factual assertions in the answer are substantiated by evidence."""
        # Check if the answer itself is an explicit declaration of lack of evidence
        is_transparent_refusal = (
            "no dispongo de informaci" in generated_answer.lower()
            or "no encontré evidencia" in generated_answer.lower()
            or "no se encontraron registros" in generated_answer.lower()
        )

        claims = self.extract_factual_claims(generated_answer)
        total_claims = len(claims)

        if total_claims == 0:
            return GroundingResult(
                is_grounded=True,
                grounding_score=1.0,
                unsupported_claims=[],
                validated_sources=context.sources[:5],
                rationale="La respuesta no contiene afirmaciones cuantitativas ni códigos que requieran verificación cruzada."
                if not is_transparent_refusal
                else "Respuesta transparente reconociendo ausencia o insuficiencia de datos.",
            )

        unsupported: list[str] = []
        for claim in claims:
            if not self._search_in_context(claim, context):
                unsupported.append(claim)

        supported_count = total_claims - len(unsupported)
        score = round(supported_count / total_claims, 4)
        is_grounded = score >= self.min_grounding_score

        # Identify validated sources that contributed to supported claims
        validated_sources: list[Source] = []
        for src in context.sources:
            for claim in claims:
                if (
                    src not in validated_sources
                    and claim not in unsupported
                    and (
                        claim.lower() in src.title.lower()
                        or (src.snippet and claim.lower() in src.snippet.lower())
                        or claim.lower() == src.id.lower()
                    )
                ):
                    validated_sources.append(src)

        rationale = (
            f"Grounding verificado: {supported_count}/{total_claims} afirmaciones respaldadas "
            f"({score:.1%})."
        )
        if unsupported:
            rationale += f" Afirmaciones no respaldadas detectadas: {', '.join(unsupported[:3])}."

        return GroundingResult(
            is_grounded=is_grounded,
            grounding_score=score,
            unsupported_claims=unsupported,
            validated_sources=validated_sources,
            rationale=rationale,
        )

    def enforce_grounding(
        self,
        answer: str,
        validation: GroundingResult,
    ) -> str:
        """Enforce strict grounding: if required and validation failed, substitute with safe fallback."""
        if self.grounding_required and not validation.is_grounded:
            return INSUFFICIENT_EVIDENCE_FALLBACK
        return answer
