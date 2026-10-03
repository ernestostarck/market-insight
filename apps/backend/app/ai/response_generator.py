"""End-to-end Response Generator for MercadoInsight AI (Fase 9.13).

Synthesizes natural, evidence-grounded responses faithfully preserving original figures,
tender codes, RUTs, and dates; extracts citations; validates grounding; and enforces
guardrails.
"""

from __future__ import annotations

import logging
import time

from app.ai.citations import CitationManager
from app.ai.contracts import (
    ChatMessage,
    Context,
    GeneratedResponse,
    GroundingResult,
    GuardrailResult,
    RetrievalResult,
)
from app.ai.grounding_validator import (
    INSUFFICIENT_EVIDENCE_FALLBACK,
    FactualGroundingValidator,
)
from app.ai.guardrails import (
    INJECTION_REJECTION_MESSAGE,
    SCOPE_REJECTION_MESSAGE,
    GuardrailEngine,
)
from app.ai.interfaces import LLMGateway

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Orchestrates evidence-grounded answer generation with safety and citation verification."""

    def __init__(
        self,
        llm_gateway: LLMGateway,
        citation_manager: CitationManager | None = None,
        grounding_validator: FactualGroundingValidator | None = None,
        guardrail_engine: GuardrailEngine | None = None,
        default_system_prompt: str | None = None,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.citation_manager = citation_manager or CitationManager()
        self.grounding_validator = grounding_validator or FactualGroundingValidator()
        self.guardrail_engine = guardrail_engine or GuardrailEngine()
        self.default_system_prompt = default_system_prompt

    async def generate_response(
        self,
        user_query: str,
        context: Context,
        retrieval_result: RetrievalResult,
        conversation_history: list[ChatMessage] | None = None,
        system_prompt: str | None = None,
        grounding_required: bool = True,
    ) -> GeneratedResponse:
        """Synthesize natural, verified response from evidence context and user query."""
        start_time = time.perf_counter()

        # 1. Input Guardrails
        input_guardrail = self.guardrail_engine.validate_input(user_query)
        if not input_guardrail.is_safe:
            msg = (
                INJECTION_REJECTION_MESSAGE
                if input_guardrail.layer == "injection"
                else SCOPE_REJECTION_MESSAGE
            )
            return GeneratedResponse(
                content=msg,
                sources=[],
                citations=[],
                guardrail=input_guardrail,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 2. Check for empty evidence / zero retrieval matches
        has_evidence = bool(
            retrieval_result.total_results > 0
            or context.sources
            or context.structured_data
        )

        if not has_evidence:
            logger.info("No evidence retrieved for query '%s'. Returning transparent refusal.", user_query[:50])
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return GeneratedResponse(
                content=INSUFFICIENT_EVIDENCE_FALLBACK,
                sources=[],
                citations=[],
                grounding=GroundingResult(
                    is_grounded=True,
                    grounding_score=1.0,
                    unsupported_claims=[],
                    validated_sources=[],
                    rationale="Respuesta honesta y transparente por ausencia de evidencia en registros de Mercado Público.",
                ),
                guardrail=GuardrailResult(is_safe=True, layer="evidence_check"),
                latency_ms=latency_ms,
            )

        # 3. LLM Gateway Generation
        sys_prompt = system_prompt or self.default_system_prompt
        chat_msg = await self.llm_gateway.generate_response(
            user_query=user_query,
            context=context,
            system_prompt=sys_prompt,
            conversation_history=conversation_history,
        )

        raw_content = chat_msg.content.strip()

        # 4. Citations Extraction & Linking
        citations = self.citation_manager.extract_citations(
            text=raw_content,
            context_sources=context.sources,
        )

        # 5. Factual Grounding Verification
        grounding_result = await self.grounding_validator.validate(
            generated_answer=raw_content,
            context=context,
        )

        # Enforce grounding if required
        final_content = raw_content
        if grounding_required and not grounding_result.is_grounded:
            logger.warning(
                "Answer failed factual grounding (score=%.2f). Unsupported: %s. Applying fallback.",
                grounding_result.grounding_score,
                grounding_result.unsupported_claims,
            )
            final_content = INSUFFICIENT_EVIDENCE_FALLBACK
            # Clear or mark citations as unverified
            citations = [c for c in citations if c.is_verified]

        # 6. Output Guardrails
        output_guardrail = self.guardrail_engine.validate_output(final_content, context)
        if not output_guardrail.is_safe:
            final_content = INSUFFICIENT_EVIDENCE_FALLBACK

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        token_usage: dict[str, int] = {
            "tokens_input": chat_msg.tokens_input or 0,
            "tokens_output": chat_msg.tokens_output or 0,
        }

        return GeneratedResponse(
            content=final_content,
            sources=context.sources,
            citations=citations,
            grounding=grounding_result,
            guardrail=output_guardrail,
            latency_ms=latency_ms,
            model=chat_msg.model,
            token_usage=token_usage,
        )
