export type AIChatRole = 'user' | 'assistant' | 'system';

export interface AIChatMessage {
  id: string;
  role: AIChatRole;
  content: string;
  timestamp: string;
  referencedTenders?: Array<{
    id: number;
    codigo: string;
    nombre: string;
  }>;
}

export interface AIExecutiveSummary {
  tenderId: number;
  codigo: string;
  summary: string;
  relevanceScore: number;
  recommendations: string[];
  keyRiskFactors: string[];
}

export interface AIModelMetrics {
  totalInferences: number;
  averageLatencyMs: number;
  accuracyRate: number;
  activeModelName: string;
}

// 7.26 & 7.27 Módulo IA / NLP y Revisión Humana — real shape of `/ai/reviews`
// (app/services/nlp/review.py's ReviewService, backed by knowledge.classifications
// joined with core.licitacion/core.organismo). No document/attachment ingestion
// exists, so there is no real "nombre_archivo"; no per-item entity/product
// extraction is persisted, so `explanation` (the classifier's own real reasoning)
// and `item_names` (real core.licitacion_item names) stand in for that instead.
export type AIConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';
export type AIRelevanceTier = 'high' | 'medium' | 'low' | 'not_relevant';

export interface AIReviewQueueItem {
  classification_id: string;
  licitacion_id: number;
  licitacion_codigo: string | null;
  title: string | null;
  organismo: string | null;
  monto_estimado: number | null;
  item_names: string[];
  confidence_score: number; // 0 - 1
  confidence_level: AIConfidenceLevel;
  relevance_score: number | null;
  relevance_tier: AIRelevanceTier | null;
  category_code: string | null;
  subcategory_code: string | null;
  winning_method: string | null;
  rule_score: number | null;
  similarity_score: number | null;
  model_score: number | null;
  explanation: Record<string, unknown> | null;
  needs_review: boolean;
  review_reasons: string[];
  priority_score: number;
}

export interface AIReviewStats {
  total_reviews: number;
  accepted_count: number;
  modified_count: number;
  acceptance_rate: number;
  unreviewed_classifications: number;
}

export interface AIReviewAcceptAction {
  classificationId: string;
  reason?: string;
}

export interface AIReviewModifyAction {
  classificationId: string;
  categoryCode: string;
  subcategoryCode?: string;
  relevant?: boolean;
  relevanceTier?: string;
  reason: string;
}

export interface AIFilters {
  q?: string;
}

// 7.28 Estado y Calidad de los Datos — real shape of GET /system/status
// (app/schemas/system.py's SystemStatusResponse). No document/classification
// counters exist here (that lives in /ai/reviews/stats, used elsewhere);
// this endpoint is strictly operational health + ETL freshness + quality score.
export type ComponentStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface ComponentHealth {
  status: ComponentStatus;
  message: string | null;
  latency_ms: number | null;
  details?: Record<string, unknown> | null;
}

export interface ETLStatusSummary {
  status: 'healthy' | 'degraded' | 'stale' | 'failed';
  last_run_timestamp: string | null;
  data_freshness_seconds: number | null;
}

export interface DataQualityStatusSummary {
  score: number;
  status: 'healthy' | 'degraded' | 'critical';
  last_evaluated: string | null;
}

export interface LayerAvailability {
  status: ComponentStatus;
  reasons: string[];
}

export interface AvailabilitySummary {
  technical: LayerAvailability;
  data: LayerAvailability;
}

export interface SystemStatus {
  status: ComponentStatus;
  timestamp: string;
  app_name: string;
  version: string;
  environment: string;
  components: Record<string, ComponentHealth>;
  etl: ETLStatusSummary;
  data_quality: DataQualityStatusSummary;
  availability: AvailabilitySummary;
}

// 9.14 Citations & Sources
export interface AICitation {
  id: string;
  source_id: string;
  source_type: string;
  title: string;
  snippet?: string | null;
  relevance?: number | null;
  url?: string | null;
  claim_text?: string | null;
  target_route?: string | null;
  is_verified: boolean;
}

export interface AISource {
  id: string;
  source_type: string;
  title: string;
  snippet?: string | null;
  score?: number | null;
  url?: string | null;
  metadata?: Record<string, unknown>;
}
