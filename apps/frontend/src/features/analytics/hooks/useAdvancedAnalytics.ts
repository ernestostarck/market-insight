import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  CategorySpendingRead,
  CompetitionSummaryRead,
  MarketMonthlyRead,
  SupplierPerformanceRead,
} from '@/types/analytics';

export interface AdvancedAnalyticsData {
  marketOverview: {
    serieTemporal: Array<{ mes: string; monto: number; licitaciones: number; adjudicaciones: number }>;
    estacionalidad: Array<{ trimestre: string; monto: number; porcentaje: number }>;
    tasaAdjudicacionEfectiva: number | null;
  };
  supplierAnalysis: {
    indiceHHI: number | null;
    nivelConcentracion: string;
    topProveedores: Array<{
      razon_social: string;
      rut: string;
      cuota: number;
      monto: number;
      ratioAdjudicacionPromedio: number | null;
    }>;
  };
  categoryAnalysis: {
    distribucion: Array<{ categoria: string; monto: number; porcentaje: number; color: string }>;
  };
  competitionAnalysis: {
    oferentesPromedio: number | null;
    margenDescuentoPromedio: number | null;
    totalAdjudicacionesConOferentes: number;
    distribucionOfertas: Array<{ rango_oferentes: string; porcentaje_procesos: number }>;
  };
}

const PALETTE = ['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#14b8a6', '#f97316'];

export function useAdvancedAnalytics() {
  return useQuery<AdvancedAnalyticsData>({
    queryKey: ['advanced-analytics'],
    queryFn: async () => {
      const [monthly, suppliers, categories, competition] = await Promise.all([
        api.get<MarketMonthlyRead[]>('/analytics/market/monthly', { params: { limit: 1000 } }),
        api.get<SupplierPerformanceRead[]>('/analytics/suppliers/performance', { params: { limit: 500 } }),
        api.get<CategorySpendingRead[]>('/analytics/categories/spending', { params: { limit: 200 } }),
        api.get<CompetitionSummaryRead>('/analytics/competition/summary'),
      ]);

      const orderedMonthly = [...monthly].sort((a, b) => a.mes.localeCompare(b.mes));
      const serieTemporal = orderedMonthly.map((m) => ({
        mes: formatMonthLabel(m.mes),
        monto: Number(m.monto_total_adjudicado),
        licitaciones: m.total_licitaciones,
        adjudicaciones: m.total_adjudicaciones,
      }));
      const estacionalidad = buildEstacionalidad(orderedMonthly);
      const totalLic = monthly.reduce((acc, m) => acc + m.total_licitaciones, 0);
      const totalAdj = monthly.reduce((acc, m) => acc + m.total_adjudicaciones, 0);
      const tasaAdjudicacionEfectiva = totalLic > 0 ? (totalAdj / totalLic) * 100 : null;

      const totalMontoProveedores = suppliers.reduce(
        (acc, s) => acc + Number(s.monto_total_adjudicado),
        0,
      );
      const topProveedores = [...suppliers]
        .sort((a, b) => Number(b.monto_total_adjudicado) - Number(a.monto_total_adjudicado))
        .slice(0, 10)
        .map((s) => ({
          razon_social: s.razon_social,
          rut: s.rut,
          monto: Number(s.monto_total_adjudicado),
          cuota:
            totalMontoProveedores > 0
              ? (Number(s.monto_total_adjudicado) / totalMontoProveedores) * 100
              : 0,
          ratioAdjudicacionPromedio:
            s.ratio_adjudicacion_promedio != null ? Number(s.ratio_adjudicacion_promedio) * 100 : null,
        }));
      const indiceHHI =
        totalMontoProveedores > 0
          ? suppliers.reduce((acc, s) => {
              const share = (Number(s.monto_total_adjudicado) / totalMontoProveedores) * 100;
              return acc + share * share;
            }, 0)
          : null;

      const totalMontoCategorias = categories.reduce((acc, c) => acc + Number(c.gasto_total_oc), 0);
      const distribucion = [...categories]
        .sort((a, b) => Number(b.gasto_total_oc) - Number(a.gasto_total_oc))
        .slice(0, 8)
        .map((c, idx) => ({
          categoria: c.categoria,
          monto: Number(c.gasto_total_oc),
          porcentaje:
            totalMontoCategorias > 0
              ? Math.round((Number(c.gasto_total_oc) / totalMontoCategorias) * 1000) / 10
              : 0,
          color: PALETTE[idx % PALETTE.length],
        }));

      return {
        marketOverview: { serieTemporal, estacionalidad, tasaAdjudicacionEfectiva },
        supplierAnalysis: { indiceHHI, nivelConcentracion: classifyHHI(indiceHHI), topProveedores },
        categoryAnalysis: { distribucion },
        competitionAnalysis: {
          oferentesPromedio: competition.oferentes_promedio,
          margenDescuentoPromedio: competition.margen_descuento_promedio,
          totalAdjudicacionesConOferentes: competition.total_adjudicaciones_con_oferentes,
          distribucionOfertas: competition.distribucion_oferentes.map((b) => ({
            rango_oferentes: b.rango_oferentes,
            porcentaje_procesos: b.porcentaje,
          })),
        },
      };
    },
    staleTime: 5 * 60 * 1000,
  });
}

function formatMonthLabel(mes: string): string {
  const [year, month] = mes.split('-').map(Number);
  const date = new Date(year, month - 1, 1);
  return date.toLocaleDateString('es-CL', { month: 'short', year: 'numeric' });
}

function buildEstacionalidad(monthly: MarketMonthlyRead[]) {
  const quarters = new Map<string, number>();
  for (const m of monthly) {
    const [year, month] = m.mes.split('-').map(Number);
    const q = Math.floor((month - 1) / 3) + 1;
    const key = `Q${q} ${year}`;
    quarters.set(key, (quarters.get(key) ?? 0) + Number(m.monto_total_adjudicado));
  }
  const total = [...quarters.values()].reduce((a, b) => a + b, 0);
  return [...quarters.entries()].map(([trimestre, monto]) => ({
    trimestre,
    monto,
    porcentaje: total > 0 ? Math.round((monto / total) * 1000) / 10 : 0,
  }));
}

function classifyHHI(hhi: number | null): string {
  if (hhi == null) return 'Sin datos suficientes';
  if (hhi < 1500) return `Mercado competitivo (HHI ${Math.round(hhi)})`;
  if (hhi < 2500) return `Concentración moderada (HHI ${Math.round(hhi)})`;
  return `Alta concentración (HHI ${Math.round(hhi)})`;
}
