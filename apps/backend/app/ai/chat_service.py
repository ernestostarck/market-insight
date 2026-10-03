"""Conversational RAG Coordinator Service for MercadoInsight AI (Fase 9.20).

Orchestrates the complete pipeline: Guardrails -> Memory/Follow-Up -> Intent -> Planner
-> Retrieval -> Context -> Generation -> Anti-Hallucination -> Persistence.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anti_hallucination import AntiHallucinationEngine
from app.ai.citations import CitationManager
from app.ai.context_builder import SecureContextBuilder
from app.ai.contracts import (
    ChatMessage,
    GeneratedResponse,
    GroundingResult,
    GuardrailResult,
    MessageRole,
    RetrievalResult,
)
from app.ai.cost_tracker import get_cost_tracker
from app.ai.follow_up import FollowUpResolver
from app.ai.grounding_validator import FactualGroundingValidator
from app.ai.guardrails import GuardrailEngine
from app.ai.intent import RuleBasedIntentDetector
from app.ai.interfaces import LLMGateway, Retriever
from app.ai.llm.gateway import LLMGateway as ConcreteLLMGateway
from app.ai.memory import ConversationMemoryManager
from app.ai.monitoring import AI_GUARDRAIL_BLOCKS_TOTAL, record_rag_turn_metrics
from app.ai.planner import DeterministicQueryPlanner
from app.ai.response_generator import ResponseGenerator
from app.ai.security import (
    ConversationAccessController,
    PIISanitizer,
    SecurityAuditLogger,
)
from app.ai.session_service import SessionService

logger = logging.getLogger(__name__)


class ChatService:
    """End-to-end coordinator for conversational chat turns, memory, and SSE streaming."""

    def __init__(
        self,
        llm_gateway: LLMGateway | None = None,
        retriever: Retriever | None = None,
        intent_detector: RuleBasedIntentDetector | None = None,
        query_planner: DeterministicQueryPlanner | None = None,
        context_builder: SecureContextBuilder | None = None,
        guardrail_engine: GuardrailEngine | None = None,
        memory_manager: ConversationMemoryManager | None = None,
        follow_up_resolver: FollowUpResolver | None = None,
        citation_manager: CitationManager | None = None,
        grounding_validator: FactualGroundingValidator | None = None,
        anti_hallucination_engine: AntiHallucinationEngine | None = None,
        response_generator: ResponseGenerator | None = None,
    ) -> None:
        self.llm_gateway = llm_gateway or ConcreteLLMGateway()
        self.retriever = retriever
        self.intent_detector = intent_detector or RuleBasedIntentDetector()
        self.query_planner = query_planner or DeterministicQueryPlanner()
        self.context_builder = context_builder or SecureContextBuilder()
        self.guardrail_engine = guardrail_engine or GuardrailEngine()
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.follow_up_resolver = follow_up_resolver or FollowUpResolver()
        self.citation_manager = citation_manager or CitationManager()
        self.grounding_validator = grounding_validator or FactualGroundingValidator()
        self.anti_hallucination = anti_hallucination_engine or AntiHallucinationEngine(
            grounding_validator=self.grounding_validator
        )
        self.response_generator = response_generator or ResponseGenerator(
            llm_gateway=self.llm_gateway,
            citation_manager=self.citation_manager,
            grounding_validator=self.grounding_validator,
            guardrail_engine=self.guardrail_engine,
        )

    async def execute_chat_turn(
        self,
        query: str,
        conversation_id: UUID,
        user_id: UUID,
        db: AsyncSession,
        session_service: SessionService,
    ) -> tuple[ChatMessage, GeneratedResponse]:
        """Execute a full conversational RAG turn and atomically persist the final messages."""
        # 1. Acquire or load conversation session
        conv_session = await session_service.aget_or_create_session(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        ConversationAccessController.verify_ownership(conv_session.user_id, user_id)

        # 2. Extract conversation context state
        context_state = self.memory_manager.get_context_state(conv_session.metadata)

        # 3. Resolve follow-up references
        follow_up = self.follow_up_resolver.resolve(query, context_state)

        # If genuine ambiguity requires clarification
        if follow_up.needs_clarification and follow_up.clarification_message:
            clarification_resp = GeneratedResponse(
                content=follow_up.clarification_message,
                sources=[],
                citations=[],
                grounding=GroundingResult(is_grounded=True, grounding_score=1.0, rationale="Solicitud de aclaración."),
                guardrail=GuardrailResult(is_safe=True, layer="disambiguation"),
            )
            # Save user & assistant messages
            async with session_service.acquire_conversation_lock(conversation_id):
                def _save_clarification(sync_db: Any) -> ChatMessage:
                    session_service.save_message(
                        db=sync_db,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        role=MessageRole.USER,
                        content=query,
                    )
                    return session_service.save_message(
                        db=sync_db,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        role=MessageRole.ASSISTANT,
                        content=clarification_resp.content,
                    )
                saved_msg = await db.run_sync(_save_clarification)
            return saved_msg, clarification_resp

        target_query = follow_up.resolved_query

        # PII Minimization (Fase 9.25)
        target_query, pii_detected = PIISanitizer.sanitize(target_query)
        if pii_detected:
            SecurityAuditLogger.log_event(
                "pii_sanitized",
                user_id,
                conversation_id,
                {"pii_types": pii_detected},
            )

        # 4. Input Guardrails
        input_guardrail = self.guardrail_engine.validate_input(target_query)
        if not input_guardrail.is_safe:
            AI_GUARDRAIL_BLOCKS_TOTAL.labels(layer=input_guardrail.layer).inc()
            SecurityAuditLogger.log_event(
                "guardrail_blocked",
                user_id,
                conversation_id,
                {"layer": input_guardrail.layer, "reason": input_guardrail.reason},
            )
            from app.ai.guardrails import (
                INJECTION_REJECTION_MESSAGE,
                SCOPE_REJECTION_MESSAGE,
            )
            reject_text = (
                INJECTION_REJECTION_MESSAGE
                if input_guardrail.layer == "injection"
                else SCOPE_REJECTION_MESSAGE
            )
            guard_resp = GeneratedResponse(
                content=reject_text,
                guardrail=input_guardrail,
            )
            async with session_service.acquire_conversation_lock(conversation_id):
                def _save_guard(sync_db: Any) -> ChatMessage:
                    session_service.save_message(sync_db, conversation_id, user_id, MessageRole.USER, query)
                    return session_service.save_message(sync_db, conversation_id, user_id, MessageRole.ASSISTANT, reject_text)
                saved_msg = await db.run_sync(_save_guard)
            return saved_msg, guard_resp

        # 5. Retrieve historical messages
        def _get_history(sync_db: Any) -> list[ChatMessage]:
            return session_service.get_messages(sync_db, conversation_id, user_id)

        history = await db.run_sync(_get_history)
        prompt_history = self.memory_manager.get_prompt_messages(history, context_state)

        # 6. Intent Detection & Query Planning
        intent, _ = await self.intent_detector.detect_intent(target_query, prompt_history)
        plan = await self.query_planner.plan_query(target_query, intent, prompt_history)

        # Merge follow-up delta filters
        if follow_up.merged_filters:
            plan.filters.update(follow_up.merged_filters)

        # 7. Execute Retrieval (simulate or call retriever)
        if self.retriever is not None:
            retrieval_result = await self.retriever.retrieve(plan)
        else:
            retrieval_result = RetrievalResult(
                strategy_used=plan.retrieval_strategy,
                items=[],
                sources=[],
                total_results=0,
            )

        # 8. Context Construction
        context = self.context_builder.build_context(target_query, retrieval_result)

        # 9. Response Generation
        generated = await self.response_generator.generate_response(
            user_query=target_query,
            context=context,
            retrieval_result=retrieval_result,
            conversation_history=prompt_history,
        )

        # 10. Anti-Hallucination verification & controlled regeneration if needed
        clean_content, _verification, was_regen = await self.anti_hallucination.sanitize_or_regenerate(
            user_query=target_query,
            initial_answer=generated.content,
            context=context,
            retrieval_result=retrieval_result,
            llm_gateway=self.llm_gateway,
        )
        generated.content = clean_content

        # 11. Update context state
        new_state = self.memory_manager.update_context_state(
            current_state=context_state,
            query=target_query,
            detected_entities=plan.detected_entities,
            query_filters=plan.filters,
            assistant_content=clean_content,
        )

        # 12. Calculate Cost & Telemetry (Fase 9.23, 9.24)
        cost_tracker = get_cost_tracker()
        tokens_in = generated.token_usage.get("tokens_input", 0)
        tokens_out = generated.token_usage.get("tokens_output", 0)
        model_name = generated.model or "local-deterministic"
        cost_rec = cost_tracker.record_query_cost(
            query_id=str(conversation_id),
            model=model_name,
            intent=intent.value,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        record_rag_turn_metrics(
            intent=intent.value,
            retrieval_strategy=plan.retrieval_strategy.value,
            latency_ms=generated.latency_ms,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost_rec.cost_usd,
            model=model_name,
            grounding_score=generated.grounding.grounding_score if generated.grounding else 1.0,
            is_grounded=generated.grounding.is_grounded if generated.grounding else True,
            status="success",
        )

        # 13. Persist User & Assistant messages atomically in SessionService
        async with session_service.acquire_conversation_lock(conversation_id):
            def _save_turn(sync_db: Any) -> ChatMessage:
                # Update context state in session metadata
                new_meta = self.memory_manager.persist_context_state(conv_session.metadata, new_state)
                conv_session.metadata.update(new_meta)

                session_service.save_message(
                    db=sync_db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=MessageRole.USER,
                    content=query,
                )
                return session_service.save_message(
                    db=sync_db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=MessageRole.ASSISTANT,
                    content=generated.content,
                    model=model_name,
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                    latency_ms=generated.latency_ms,
                    metadata={
                        "citations": [c.model_dump() for c in generated.citations],
                        "sources": [s.model_dump() for s in generated.sources],
                        "retrieval_strategy": plan.retrieval_strategy.value,
                        "model": model_name,
                        "cost_usd": cost_rec.cost_usd,
                        "grounding": generated.grounding.model_dump() if generated.grounding else None,
                        "was_regenerated": was_regen,
                    },
                )

            saved_msg = await db.run_sync(_save_turn)

        return saved_msg, generated

    async def stream_chat_turn(
        self,
        request: Request,
        query: str,
        conversation_id: UUID,
        user_id: UUID,
        db: AsyncSession,
        session_service: SessionService,
    ) -> AsyncGenerator[str]:
        """Stream conversational RAG progress via Server-Sent Events (SSE)."""
        # Event: Initial status
        yield f"event: status\ndata: {json.dumps({'status': 'analyzing', 'message': 'Analizando consulta y verificando seguridad...'})}\n\n"

        if await request.is_disconnected():
            logger.info("Client disconnected before planning.")
            return

        # Execute turn logic
        yield f"event: status\ndata: {json.dumps({'status': 'planning', 'message': 'Formulando plan de búsqueda...'})}\n\n"

        saved_msg, generated = await self.execute_chat_turn(
            query=query,
            conversation_id=conversation_id,
            user_id=user_id,
            db=db,
            session_service=session_service,
        )

        if await request.is_disconnected():
            logger.info("Client disconnected during generation.")
            return

        # Stream text in progressive token chunks
        words = generated.content.split(" ")
        for i, word in enumerate(words):
            if await request.is_disconnected():
                logger.info("Client disconnected during token streaming.")
                return

            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"

        # Stream citations
        for citation in generated.citations:
            yield f"event: citation\ndata: {json.dumps(citation.model_dump())}\n\n"

        # Stream grounding score
        if generated.grounding:
            yield f"event: grounding\ndata: {json.dumps({'is_grounded': generated.grounding.is_grounded, 'score': generated.grounding.grounding_score})}\n\n"

        # Event: Done with persisted message metadata
        yield f"event: done\ndata: {json.dumps({'message_id': str(saved_msg.id), 'conversation_id': str(conversation_id), 'latency_ms': generated.latency_ms})}\n\n"
