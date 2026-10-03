export type SearchEntity = 'licitacion' | 'proveedor' | 'organismo';

export interface SearchQuery {
  query: string;
  entities?: SearchEntity[];
  limit_per_entity?: number;
}

export interface SearchResult {
  entity_type: SearchEntity;
  id: number;
  title: string;
  subtitle?: string | null;
  code?: string | null;
  metadata?: Record<string, string | number | boolean | null>;
  score?: number;
  semantic_score?: number;
  keyword_score?: number;
}
