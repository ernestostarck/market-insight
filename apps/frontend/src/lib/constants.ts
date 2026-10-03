/**
 * Global Frontend Constants
 */

export const APP_CONFIG = {
  name: 'Market Insight ChileCompra',
  shortName: 'MarketInsight',
  description: 'Inteligencia de mercado para licitaciones públicas críticas en Chile',
  version: '1.0.0',
  apiBaseUrl: import.meta.env.VITE_API_URL || '/api/v1',
  defaultPageSize: 20,
  maxPageSize: 100,
} as const;

export const QUERY_KEYS = {
  auth: {
    me: ['auth', 'me'] as const,
  },
  dashboard: {
    kpis: ['dashboard', 'kpis'] as const,
    recentActivity: ['dashboard', 'recent-activity'] as const,
    summary: ['dashboard', 'summary'] as const,
  },
  licitaciones: {
    all: ['licitaciones'] as const,
    list: (params: Record<string, unknown>) => ['licitaciones', 'list', params] as const,
    detail: (id: string | number) => ['licitaciones', 'detail', id] as const,
    tracking: ['licitaciones', 'tracking'] as const,
  },
  proveedores: {
    all: ['proveedores'] as const,
    list: (params: Record<string, unknown>) => ['proveedores', 'list', params] as const,
    detail: (rut: string) => ['proveedores', 'detail', rut] as const,
  },
  organismos: {
    all: ['organismos'] as const,
    list: (params: Record<string, unknown>) => ['organismos', 'list', params] as const,
    detail: (rut: string) => ['organismos', 'detail', rut] as const,
  },
  analytics: {
    trends: (params: Record<string, unknown>) => ['analytics', 'trends', params] as const,
    prices: (params: Record<string, unknown>) => ['analytics', 'prices', params] as const,
  },
  search: {
    semantic: (query: string) => ['search', 'semantic', query] as const,
  },
  ai: {
    chatHistory: (sessionId: string) => ['ai', 'chat', sessionId] as const,
  },
} as const;

export const STORAGE_KEYS = {
  authToken: 'market_insight_auth_token',
  theme: 'market_insight_theme',
  sidebarOpen: 'market_insight_sidebar_state',
  notifications: 'market_insight_notifications',
  segmento: 'market_insight_segmento',
} as const;
