import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface PriceAnalysisFilters {
  q: string;
}

export interface PriceItem {
  licitacion_codigo: string | null;
  organismo: string | null;
  nombre: string | null;
  descripcion: string | null;
  precio_unitario: number | string | null;
  cantidad: number | string | null;
  unidad: string | null;
  fecha: string | null;
  categoria_codigo: string | null;
  categoria_nombre: string | null;
}

export interface PriceStats {
  precio_minimo: number;
  precio_maximo: number;
  precio_mediano: number;
  precio_promedio: number;
  desviacion_estandar: number;
  total_muestras: number;
  distribucion: Array<{ rango: string; count: number }>;
  evolucion_temporal: Array<{ fecha: string; precio_promedio: number; min: number; max: number }>;
  items: PriceItem[];
}

const EMPTY_STATS: PriceStats = {
  precio_minimo: 0,
  precio_maximo: 0,
  precio_mediano: 0,
  precio_promedio: 0,
  desviacion_estandar: 0,
  total_muestras: 0,
  distribucion: [],
  evolucion_temporal: [],
  items: [],
};

export function usePriceAnalysis() {
  const [filters, setFilters] = useState<PriceAnalysisFilters>({ q: '' });
  const trimmedQuery = filters.q.trim();

  const query = useQuery({
    queryKey: ['price-items', trimmedQuery],
    queryFn: () =>
      api.get<PriceItem[]>('/analytics/prices/items', { params: { q: trimmedQuery, limit: 200 } }),
    enabled: trimmedQuery.length >= 2,
    staleTime: 5 * 60 * 1000,
  });

  const items = useMemo(() => query.data ?? [], [query.data]);

  const stats: PriceStats = useMemo(() => {
    const prices = items
      .map((i) => (i.precio_unitario != null ? Number(i.precio_unitario) : null))
      .filter((p): p is number => p != null && !Number.isNaN(p))
      .sort((a, b) => a - b);
    const n = prices.length;
    if (n === 0) return { ...EMPTY_STATS, items };

    const min = prices[0];
    const max = prices[n - 1];
    const mediano = n % 2 === 0 ? (prices[n / 2 - 1] + prices[n / 2]) / 2 : prices[Math.floor(n / 2)];
    const promedio = prices.reduce((acc, v) => acc + v, 0) / n;
    const variance =
      n > 1 ? prices.reduce((acc, v) => acc + (v - promedio) ** 2, 0) / (n - 1) : 0;
    const desv = Math.sqrt(variance);

    // Real, data-driven buckets (5 equal-width bands from the actual min/max found)
    const bucketSize = (max - min) / 5 || 1;
    const distribucion = Array.from({ length: 5 }, (_, idx) => {
      const lo = min + idx * bucketSize;
      const hi = idx === 4 ? max : lo + bucketSize;
      const count = prices.filter((p) => (idx === 4 ? p >= lo && p <= hi : p >= lo && p < hi)).length;
      return { rango: `${formatCompact(lo)} - ${formatCompact(hi)}`, count };
    });

    const byMonth = new Map<string, number[]>();
    for (const item of items) {
      if (!item.fecha || item.precio_unitario == null) continue;
      const price = Number(item.precio_unitario);
      if (Number.isNaN(price)) continue;
      const key = item.fecha.slice(0, 7); // YYYY-MM
      const bucket = byMonth.get(key) ?? [];
      bucket.push(price);
      byMonth.set(key, bucket);
    }
    const evolucion_temporal = [...byMonth.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([mes, values]) => ({
        fecha: mes,
        precio_promedio: values.reduce((acc, v) => acc + v, 0) / values.length,
        min: Math.min(...values),
        max: Math.max(...values),
      }));

    return {
      precio_minimo: min,
      precio_maximo: max,
      precio_mediano: mediano,
      precio_promedio: promedio,
      desviacion_estandar: desv,
      total_muestras: n,
      distribucion,
      evolucion_temporal,
      items,
    };
  }, [items]);

  return {
    filters,
    setFilters,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    hasSearched: trimmedQuery.length >= 2,
    stats,
  };
}

function formatCompact(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`;
  return `$${Math.round(value)}`;
}
