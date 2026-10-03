"""Anti-Hallucination Engine for MercadoInsight AI (Fase 9.17).

Provides deep verification of factual claims (numbers, dates, entities, procurement codes,
SQL aggregations), controlled one-shot regeneration on grounding failures, and transparent
insufficient-evidence fallbacks.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from app.ai.contracts import Context, RetrievalResult
from app.ai.grounding_validator import (
    INSUFFICIENT_EVIDENCE_FALLBACK,
    FactualGroundingValidator,
)
from app.ai.interfaces import LLMGateway

logger = logging.getLogger(__name__)

# System prompt directive for anti-hallucination regeneration
REGENERATION_SYSTEM_DIRECTIVE = """Eres MercadoInsight AI en modo de máxima rigurosidad y fidelidad documental.
La respuesta anterior fue RECHAZADA por el validador anti-alucinaciones debido a que contenía afirmaciones fácticas, montos o códigos no respaldados por la evidencia oficial.
Reglas estrictas de regeneración:
1. Responde basándote EXCLUSIVAMENTE en los datos verificados del contexto provisto.
2. Si un número, fecha, RUT o dato específico no aparece textualmente en el contexto o tabla SQL, OMITELO y declara con transparencia: "No hay información suficiente sobre [dato]".
3. Prohibido adivinar, aproximar o extrapolar cifras.
"""


class ClaimsVerificationResult(BaseModel):
    """Detailed audit of factual statements in an answer against evidence."""

    is_valid: bool = Field(..., description="True if all claims are verified by evidence.")
    total_claims: int = Field(default=0, description="Total factual claims detected.")
    verified_claims: list[str] = Field(default_factory=list, description="Claims substantiated by context.")
    unsupported_claims: list[str] = Field(default_factory=list, description="Claims without evidence in context.")
    discrepancy_types: list[str] = Field(default_factory=list, description="Categories of discrepancies detected.")
    rationale: str = Field(default="", description="Audit diagnosis.")


class AntiHallucinationEngine:
    """Detects hallucinations in model outputs and executes controlled re-prompting."""

    def __init__(
        self,
        grounding_validator: FactualGroundingValidator | None = None,
        max_regeneration_attempts: int = 1,
    ) -> None:
        self.grounding_validator = grounding_validator or FactualGroundingValidator()
        self.max_regeneration_attempts = max_regeneration_attempts

    def verify_claims(self, answer: str, context: Context) -> ClaimsVerificationResult:
        """Examine claims against context and categorize discrepancies."""
        claims = self.grounding_validator.extract_factual_claims(answer)
        verified: list[str] = []
        unsupported: list[str] = []
        discrepancies: set[str] = set()

        for claim in claims:
            # Check if substantiated by context
            if self.grounding_validator._search_in_context(claim, context):
                verified.append(claim)
            else:
                unsupported.append(claim)
                # Categorize discrepancy
                if re.search(r"\$|\bCLP\b|\bpesos\b|\bUF\b|\bUSD\b", claim, re.IGNORECASE):
                    discrepancies.add("number/currency")
                elif re.search(r"\b(19\d{2}|20\d{2})\b", claim):
                    discrepancies.add("date/year")
                elif re.search(r"\b\d+-\d+-[A-Za-z0-9]+\b", claim):
                    discrepancies.add("tender_code")
                elif re.search(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b", claim):
                    discrepancies.add("rut/supplier")
                else:
                    discrepancies.add("factual_statement")

        # Verify SQL aggregate numbers if structured tabular data is present
        if context.structured_data and isinstance(context.structured_data, list):
            for row in context.structured_data:
                for v in row.values():
                    if isinstance(v, (int, float)) and v > 0:
                        # Ensure assistant did not alter the aggregated numbers
                        val_str = str(int(v))
                        if len(val_str) >= 4 and val_str not in re.sub(r"[^\d]", "", context.formatted_prompt_context):
                            discrepancies.add("sql_aggregation")

        is_valid = len(unsupported) == 0

        rationale = (
            f"Verificación anti-alucinaciones completada: {len(verified)}/{len(claims)} afirmaciones validadas."
        )
        if unsupported:
            rationale += f" Alucinaciones detectadas: {', '.join(unsupported[:3])}."

        return ClaimsVerificationResult(
            is_valid=is_valid,
            total_claims=len(claims),
            verified_claims=verified,
            unsupported_claims=unsupported,
            discrepancy_types=sorted(discrepancies),
            rationale=rationale,
        )

    async def sanitize_or_regenerate(
        self,
        user_query: str,
        initial_answer: str,
        context: Context,
        retrieval_result: RetrievalResult,
        llm_gateway: LLMGateway,
    ) -> tuple[str, ClaimsVerificationResult, bool]:
        """Verify output and, if hallucinations are detected, execute controlled regeneration."""
        verification = self.verify_claims(initial_answer, context)

        if verification.is_valid:
            return initial_answer, verification, False

        logger.warning(
            "Hallucinations detected in response: %s. Initiating anti-hallucination regeneration...",
            verification.unsupported_claims,
        )

        current_answer = initial_answer
        regenerated = False

        for attempt in range(self.max_regeneration_attempts):
            unsupported_summary = ", ".join(verification.unsupported_claims)
            regen_prompt = (
                f"{context.formatted_prompt_context}\n\n"
                f"### ADVERTENCIA DE CONTROL DE CALIDAD:\n"
                f"La respuesta previa contenía afirmaciones NO verificables en el registro: '{unsupported_summary}'.\n"
                f"Por favor, responde nuevamente la siguiente consulta basándote ÚNICAMENTE en la evidencia oficial anterior. "
                f"Si los antecedentes no contienen alguna cifra o detalle consultado, responde explícitamente que no hay información suficiente sin inventar.\n\n"
                f"Pregunta del usuario:\n{user_query}"
            )

            # Create special temporary context with explicit anti-hallucination warning
            regen_context = Context(
                formatted_prompt_context=regen_prompt,
                sources=context.sources,
                structured_data=context.structured_data,
                token_estimate=context.token_estimate + 100,
            )

            chat_msg = await llm_gateway.generate_response(
                user_query=user_query,
                context=regen_context,
                system_prompt=REGENERATION_SYSTEM_DIRECTIVE,
            )

            regenerated = True
            current_answer = chat_msg.content.strip()
            verification = self.verify_claims(current_answer, context)

            if verification.is_valid:
                logger.info("Regeneration attempt %d successfully resolved hallucinations.", attempt + 1)
                return current_answer, verification, True

        # If after regeneration attempts the answer is still not clean, enforce safe lack of info fallback
        logger.warning("Regeneration failed to eliminate hallucinations. Falling back to safe lack of evidence.")
        return INSUFFICIENT_EVIDENCE_FALLBACK, verification, regenerated
