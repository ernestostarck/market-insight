import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface MarketObjectiveKpis {
  licitaciones_relacionadas: number;
  monto_total: number;
  proveedores_activos: number;
  organismos_activos: number;
  precio_promedio: number | null;
}

export interface MarketObjectiveTrendPoint {
  mes: string;
  monto: number;
  licitaciones: number;
}

export interface MarketObjectiveLeader {
  nombre: string;
  rut: string | null;
  monto_total: number;
  porcentaje: number;
  contratos: number;
}

export interface MarketObjectiveCategoryShare {
  codigo: string | null;
  nombre: string | null;
  monto: number;
  porcentaje: number;
}

export interface MarketObjectiveData {
  kpis: MarketObjectiveKpis;
  tasa_crecimiento: number | null;
  tendencias: MarketObjectiveTrendPoint[];
  organismos_lideres: MarketObjectiveLeader[];
  proveedores_lideres: MarketObjectiveLeader[];
  categorias_relacionadas: MarketObjectiveCategoryShare[];
  dictionary_terms_used: number;
}

export function useMarketObjective() {
  return useQuery<MarketObjectiveData>({
    queryKey: ['market-objective-disability-geriatrics'],
    queryFn: () => api.get<MarketObjectiveData>('/analytics/market-objective'),
    staleTime: 5 * 60 * 1000,
  });
}
