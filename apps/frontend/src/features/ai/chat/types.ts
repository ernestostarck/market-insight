/**
 * Type definitions for MercadoInsight Conversational RAG (Fase 9.28).
 */

export interface Conversation {
  id: string;
  user_id?: string;
  title?: string;
  status: 'active' | 'archived' | 'closed';
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  model?: string;
  tokens_input?: number;
  tokens_output?: number;
  latency_ms?: number;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface SourceItem {
  id: string;
  title: string;
  organismo?: string;
  monto_total?: number;
  relevance_score?: number;
  chunk_text?: string;
  url?: string;
}

export interface CitationItem {
  source_id: string;
  fact: string;
  page?: number;
  score?: number;
}

export interface GroundingInfo {
  supported: boolean;
  grounding_ratio?: number;
  unsupported_claims?: string[];
  reason?: string;
}

export interface TurnMetrics {
  latency_ms: number;
  retrieval_ms: number;
  tokens_input: number;
  tokens_output: number;
}

export interface ChatResponsePayload {
  conversation_id: string;
  message_id?: string;
  answer?: string;
  message: ChatMessage;
  sources: SourceItem[];
  citations: CitationItem[];
  metrics: TurnMetrics;
  grounding?: GroundingInfo;
  sources_count: number;
}

export interface MessageFeedbackPayload {
  message_id: string;
  rating: 1 | -1;
  reason?: string;
  comment?: string;
}
