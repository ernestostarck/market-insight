"""MercadoInsight AI Conversational Engine (Fase 9).

Provides natural language querying, retrieval-augmented generation (RAG),
structured SQL analysis integration, hybrid search, reranking, context assembly,
citations linking, factual grounding validation, multi-layer guardrails,
evidence-grounded response generation, anti-hallucination verification,
layered conversation memory, follow-up disambiguation, and chat streaming.
"""

from __future__ import annotations

from app.ai.anti_hallucination import (
    AntiHallucinationEngine,
    ClaimsVerificationResult,
)
from app.ai.chat_service import ChatService
from app.ai.citations import CitationManager
from app.ai.context_builder import SecureContextBuilder
from app.ai.contracts import (
    SUPPORTED_DIMENSIONS,
    SUPPORTED_METRICS,
    ChatMessage,
    Citation,
    Context,
    ConversationSession,
    ConversationStatus,
    GeneratedResponse,
    GroundingResult,
    GuardrailResult,
    IntentType,
    MessageRole,
    QueryPlan,
    RetrievalResult,
    RetrievalStrategy,
    Source,
    UnsupportedMetricError,
)
from app.ai.cost_tracker import (
    CostTracker,
    ModelPricing,
    QueryCostRecord,
    get_cost_tracker,
)
from app.ai.evaluation.dataset import (
    EvaluationCategory,
    EvaluationDataset,
    EvaluationTestCase,
)
from app.ai.evaluation.evaluator import (
    BenchmarkSummary,
    RAGEvaluator,
    TestCaseEvaluationResult,
)
from app.ai.feedback import FeedbackService, get_feedback_service
from app.ai.follow_up import FollowUpResolution, FollowUpResolver
from app.ai.grounding_validator import (
    INSUFFICIENT_EVIDENCE_FALLBACK,
    FactualGroundingValidator,
)
from app.ai.guardrails import (
    DataBoundariesGuardrail,
    GuardrailEngine,
    PromptInjectionGuardrail,
    ScopeGuardrail,
    SQLBoundariesGuardrail,
)
from app.ai.hybrid_retriever import HybridRetriever
from app.ai.intent import RuleBasedIntentDetector
from app.ai.llm.gateway import LLMGateway
from app.ai.memory import ConversationContextState, ConversationMemoryManager
from app.ai.metrics import (
    compute_answer_relevance,
    compute_citation_accuracy,
    compute_context_relevance,
    compute_faithfulness,
    compute_grounding_rate,
    compute_mrr,
    compute_ndcg,
    compute_precision_at_k,
    compute_recall_at_k,
)
from app.ai.planner import DeterministicQueryPlanner
from app.ai.prompts.templates import (
    GUARDRAIL_PROMPT_TEMPLATE_V1,
    RAG_PROMPT_TEMPLATE_V1,
    SQL_PROMPT_TEMPLATE_V1,
    SYSTEM_PROMPT_V1,
)
from app.ai.reranker import Reranker, RerankingMetrics
from app.ai.response_generator import ResponseGenerator
from app.ai.security import (
    ConversationAccessController,
    PIISanitizer,
    SecurityAuditLogger,
)
from app.ai.semantic_retriever import SemanticRetriever
from app.ai.sql_retriever import SQLRetriever

__all__ = [
    "GUARDRAIL_PROMPT_TEMPLATE_V1",
    "INSUFFICIENT_EVIDENCE_FALLBACK",
    "RAG_PROMPT_TEMPLATE_V1",
    "SQL_PROMPT_TEMPLATE_V1",
    "SUPPORTED_DIMENSIONS",
    "SUPPORTED_METRICS",
    "SYSTEM_PROMPT_V1",
    "AntiHallucinationEngine",
    "BenchmarkSummary",
    "ChatMessage",
    "ChatService",
    "Citation",
    "CitationManager",
    "ClaimsVerificationResult",
    "Context",
    "ConversationAccessController",
    "ConversationContextState",
    "ConversationMemoryManager",
    "ConversationSession",
    "ConversationStatus",
    "CostTracker",
    "DataBoundariesGuardrail",
    "DeterministicQueryPlanner",
    "EvaluationCategory",
    "EvaluationDataset",
    "EvaluationTestCase",
    "FactualGroundingValidator",
    "FeedbackService",
    "FollowUpResolution",
    "FollowUpResolver",
    "GeneratedResponse",
    "GroundingResult",
    "GuardrailEngine",
    "GuardrailResult",
    "HybridRetriever",
    "IntentType",
    "LLMGateway",
    "MessageRole",
    "ModelPricing",
    "PIISanitizer",
    "PromptInjectionGuardrail",
    "QueryCostRecord",
    "QueryPlan",
    "RAGEvaluator",
    "Reranker",
    "RerankingMetrics",
    "ResponseGenerator",
    "RetrievalResult",
    "RetrievalStrategy",
    "RuleBasedIntentDetector",
    "SQLBoundariesGuardrail",
    "SQLRetriever",
    "ScopeGuardrail",
    "SecureContextBuilder",
    "SecurityAuditLogger",
    "SemanticRetriever",
    "Source",
    "TestCaseEvaluationResult",
    "UnsupportedMetricError",
    "compute_answer_relevance",
    "compute_citation_accuracy",
    "compute_context_relevance",
    "compute_faithfulness",
    "compute_grounding_rate",
    "compute_mrr",
    "compute_ndcg",
    "compute_precision_at_k",
    "compute_recall_at_k",
    "get_cost_tracker",
    "get_feedback_service",
]
