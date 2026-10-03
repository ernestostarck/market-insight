import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { QUERY_KEYS } from '@/lib/constants';
import type {
  MarketMonthlyRead,
  SupplierPerformanceRead,
  CategorySpendingRead,
  DashboardKpis,
} from '@/types/analytics';
import type { Licitacion } from '@/types/licitacion';
import type { Adjudicacion } from '@/types/adjudicacion';
import type { CursorPage } from '@/types/common';
import { useSegmento } from '@/features/segmento';
import { useGlobalFilters } from '@/components/filters/useGlobalFilters';
import type { MarketObjectiveData } from '@/features/analytics/hooks/useMarketObjective';

// Default fallback data tailored to ChileCompra Geriatric & Disability procurement
const FALLBACK_KPIS: DashboardKpis = {
  licitaciones_activas: 142,
  monto_total_adjudicado_mes: 1845000000, // $1.845M CLP
  proveedores_activos: 86,
  organismos_compradores: 34,
  tasa_crecimiento_monto: 14.8,
  match_semantico_promedio: 94.2,
};

const FALLBACK_MONTHLY: MarketMonthlyRead[] = [
  {
    mes: '2026-01-01',
    total_licitaciones: 112,
    total_adjudicaciones: 78,
    monto_total_adjudicado: 1150000000,
  },
  {
    mes: '2026-02-01',
    total_licitaciones: 124,
    total_adjudicaciones: 84,
    monto_total_adjudicado: 1320000000,
  },
  {
    mes: '2026-03-01',
    total_licitaciones: 130,
    total_adjudicaciones: 91,
    monto_total_adjudicado: 1480000000,
  },
  {
    mes: '2026-04-01',
    total_licitaciones: 118,
    total_adjudicaciones: 80,
    monto_total_adjudicado: 1290000000,
  },
  {
    mes: '2026-05-01',
    total_licitaciones: 145,
    total_adjudicaciones: 104,
    monto_total_adjudicado: 1720000000,
  },
  {
    mes: '2026-06-01',
    total_licitaciones: 156,
    total_adjudicaciones: 112,
    monto_total_adjudicado: 1845000000,
  },
];

const FALLBACK_SUPPLIERS: SupplierPerformanceRead[] = [
  {
    razon_social: 'Ortopedia Técnica Chile SpA',
    rut: '761234567',
    total_adjudicaciones: 34,
    monto_total_adjudicado: 450000000,
    ratio_adjudicacion_promedio: 0.94,
  },
  {
    razon_social: 'Equipamiento Médico Geriatrico Ltda',
    rut: '769876543',
    total_adjudicaciones: 28,
    monto_total_adjudicado: 380000000,
    ratio_adjudicacion_promedio: 0.91,
  },
  {
    razon_social: 'Movilidad & Cuidado Mayor S.A.',
    rut: '774561230',
    total_adjudicaciones: 22,
    monto_total_adjudicado: 310000000,
    ratio_adjudicacion_promedio: 0.88,
  },
  {
    razon_social: 'Insumos Clínicos del Pacífico SpA',
    rut: '763334445',
    total_adjudicaciones: 19,
    monto_total_adjudicado: 240000000,
    ratio_adjudicacion_promedio: 0.96,
  },
  {
    razon_social: 'Tecnología Asistiva Austral',
    rut: '768889991',
    total_adjudicaciones: 15,
    monto_total_adjudicado: 195000000,
    ratio_adjudicacion_promedio: 0.92,
  },
];

const FALLBACK_CATEGORIES: CategorySpendingRead[] = [
  {
    categoria: 'Camas Clínicas & Colchones Antiescaras',
    codigo_categoria: '42191801',
    gasto_total_oc: 620000000,
    numero_ordenes_compra: 42,
    gasto_promedio_oc: 14761904,
  },
  {
    categoria: 'Sillas de Ruedas Eléctricas y Manuales',
    codigo_categoria: '42211506',
    gasto_total_oc: 480000000,
    numero_ordenes_compra: 38,
    gasto_promedio_oc: 12631578,
  },
  {
    categoria: 'Barras de Seguridad y Apoyo Ergonómico',
    codigo_categoria: '42211509',
    gasto_total_oc: 310000000,
    numero_ordenes_compra: 55,
    gasto_promedio_oc: 5636363,
  },
  {
    categoria: 'Grúas de Transferencia de Pacientes',
    codigo_categoria: '42192404',
    gasto_total_oc: 260000000,
    numero_ordenes_compra: 18,
    gasto_promedio_oc: 14444444,
  },
  {
    categoria: 'Monitores de Signos Vitales para Eleam',
    codigo_categoria: '42181801',
    gasto_total_oc: 175000000,
    numero_ordenes_compra: 24,
    gasto_promedio_oc: 7291666,
  },
];

const FALLBACK_RECENT_TENDERS: Licitacion[] = [
  {
    id: 101,
    codigo: '1057-22-LR26',
    nombre: 'Suministro de Camas Clínicas Hospitalarias y Accesorios Antiescaras',
    estado: 'publicada',
    monto_estimado: 125000000,
    fecha_publicacion: '2026-06-18',
    organismo_id: 1,
    organismo: { id: 1, codigo: 'H01', nombre: 'Hospital Clínico San Borja Arriarán' },
  },
  {
    id: 102,
    codigo: '2234-15-LE26',
    nombre: 'Adquisición de Sillas de Ruedas Bariátricas para Centros ELEAM',
    estado: 'adjudicada',
    monto_estimado: 78000000,
    fecha_publicacion: '2026-06-15',
    organismo_id: 2,
    organismo: { id: 2, codigo: 'SENAMA', nombre: 'Servicio Nacional del Adulto Mayor' },
  },
  {
    id: 103,
    codigo: '654-10-L126',
    nombre: 'Implementación de Baños Adaptados y Barras Antideslizantes',
    estado: 'publicada',
    monto_estimado: 45000000,
    fecha_publicacion: '2026-06-14',
    organismo_id: 3,
    organismo: { id: 3, codigo: 'MUNI-STGO', nombre: 'Municipalidad de Santiago' },
  },
  {
    id: 104,
    codigo: '1890-44-LP26',
    nombre: 'Servicio de Mantenimiento Preventivo de Grúas y Elevadores de Pacientes',
    estado: 'cerrada',
    monto_estimado: 32000000,
    fecha_publicacion: '2026-06-10',
    organismo_id: 4,
    organismo: { id: 4, codigo: 'H-SALV', nombre: 'Hospital del Salvador' },
  },
];

const FALLBACK_RECENT_AWARDS: Adjudicacion[] = [
  {
    id: 201,
    licitacion_id: 102,
    licitacion_codigo: '2234-15-LE26',
    licitacion_nombre: 'Adquisición de Sillas de Ruedas Bariátricas',
    proveedor_id: 1,
    proveedor_rut: '76.123.456-7',
    proveedor_razon_social: 'Ortopedia Técnica Chile SpA',
    organismo_id: 2,
    organismo_nombre: 'SENAMA',
    monto_adjudicado: 74500000,
    fecha_adjudicacion: '2026-06-19',
  },
  {
    id: 202,
    licitacion_id: 98,
    licitacion_codigo: '3310-8-LP26',
    licitacion_nombre: 'Equipamiento de Terapia Ocupacional para Discapacidad',
    proveedor_id: 2,
    proveedor_rut: '76.987.654-3',
    proveedor_razon_social: 'Equipamiento Médico Geriatrico Ltda',
    organismo_id: 5,
    organismo_nombre: 'Instituto Nacional de Rehabilitación Pedro Aguirre Cerda',
    monto_adjudicado: 58200000,
    fecha_adjudicacion: '2026-06-17',
  },
  {
    id: 203,
    licitacion_id: 95,
    licitacion_codigo: '1120-19-LE26',
    licitacion_nombre: 'Colchones de Presión Alterna para Pacientes Postrados',
    proveedor_id: 3,
    proveedor_rut: '77.456.123-0',
    proveedor_razon_social: 'Movilidad & Cuidado Mayor S.A.',
    organismo_id: 1,
    organismo_nombre: 'Hospital Clínico San Borja Arriarán',
    monto_adjudicado: 43000000,
    fecha_adjudicacion: '2026-06-15',
  },
];

// The demo fallbacks describe the geriatría niche: with a rubro selected, an empty
// API answer is a real "no data for this rubro" and must not be replaced by them.
function orFallback<T>(res: T[] | undefined, fallback: T[], scoped: boolean): T[] {
  if (res && res.length > 0) return res;
  return scoped ? (res ?? []) : fallback;
}

/** '2026-03-17' -> '2026-03-01': market/monthly compares whole months. */
const monthStart = (isoDate?: string) => (isoDate ? `${isoDate.slice(0, 7)}-01` : undefined);

export function useDashboardData() {
  const segmento = useSegmento();
  const { filters } = useGlobalFilters();
  // With a rubro or any global filter active, an empty answer is real (see orFallback).
  const scoped =
    segmento !== null ||
    Boolean(
      filters.startDate ||
      filters.endDate ||
      filters.proveedor ||
      filters.organismo ||
      filters.estado ||
      filters.montoMin,
    );

  const monthlyParams = {
    start_month: monthStart(filters.startDate),
    end_month: monthStart(filters.endDate),
  };
  const proveedorQuery = filters.proveedor?.trim();
  const suppliersParams = {
    query: proveedorQuery && proveedorQuery.length >= 2 ? proveedorQuery : undefined,
  };
  const tendersParams = {
    limit: 4,
    q: filters.organismo?.trim() || undefined,
    estado: filters.estado || undefined,
    monto_min: filters.montoMin,
  };

  // Real KPIs for the selected rubro (the unscoped dashboard keeps its demo KPIs).
  const kpisQuery = useQuery({
    queryKey: ['analytics', 'market-objective', 'dashboard-kpis'],
    queryFn: () => api.get<MarketObjectiveData>('/analytics/market-objective'),
    enabled: segmento !== null,
  });
  // Monthly trends query
  const monthlyQuery = useQuery({
    queryKey: QUERY_KEYS.analytics.trends(monthlyParams),
    queryFn: async () => {
      try {
        const res = await api.get<MarketMonthlyRead[]>('/analytics/market/monthly', {
          params: monthlyParams,
        });
        return orFallback(res, FALLBACK_MONTHLY, scoped);
      } catch {
        if (scoped) throw new Error('No se pudieron cargar los datos del rubro');
        return FALLBACK_MONTHLY;
      }
    },
  });

  // Top suppliers query
  const suppliersQuery = useQuery({
    queryKey: ['analytics', 'suppliers', 'performance', suppliersParams],
    queryFn: async () => {
      try {
        const res = await api.get<SupplierPerformanceRead[]>('/analytics/suppliers/performance', {
          params: suppliersParams,
        });
        return orFallback(res, FALLBACK_SUPPLIERS, scoped);
      } catch {
        if (scoped) throw new Error('No se pudieron cargar los datos del rubro');
        return FALLBACK_SUPPLIERS;
      }
    },
  });

  // Top categories query
  const categoriesQuery = useQuery({
    queryKey: ['analytics', 'categories', 'spending'],
    queryFn: async () => {
      try {
        const res = await api.get<CategorySpendingRead[]>('/analytics/categories/spending');
        return orFallback(res, FALLBACK_CATEGORIES, scoped);
      } catch {
        if (scoped) throw new Error('No se pudieron cargar los datos del rubro');
        return FALLBACK_CATEGORIES;
      }
    },
  });

  // Recent tenders query
  const recentTendersQuery = useQuery({
    queryKey: QUERY_KEYS.licitaciones.list(tendersParams),
    queryFn: async () => {
      try {
        const res = await api.get<CursorPage<Licitacion> | Licitacion[]>('/licitaciones', {
          params: tendersParams,
        });
        return orFallback(Array.isArray(res) ? res : res?.data, FALLBACK_RECENT_TENDERS, scoped);
      } catch {
        if (scoped) throw new Error('No se pudieron cargar las licitaciones del rubro');
        return FALLBACK_RECENT_TENDERS;
      }
    },
  });

  const refetchAll = async () => {
    await Promise.all([
      monthlyQuery.refetch(),
      suppliersQuery.refetch(),
      categoriesQuery.refetch(),
      recentTendersQuery.refetch(),
    ]);
  };

  const isLoading =
    monthlyQuery.isLoading ||
    suppliersQuery.isLoading ||
    categoriesQuery.isLoading ||
    recentTendersQuery.isLoading;

  const isFetching =
    monthlyQuery.isFetching ||
    suppliersQuery.isFetching ||
    categoriesQuery.isFetching ||
    recentTendersQuery.isFetching;

  const scopedKpis = kpisQuery.data?.kpis;
  const kpis: DashboardKpis =
    segmento && scopedKpis
      ? {
          licitaciones_activas: scopedKpis.licitaciones_relacionadas,
          monto_total_adjudicado_mes: scopedKpis.monto_total,
          proveedores_activos: scopedKpis.proveedores_activos,
          organismos_compradores: scopedKpis.organismos_activos,
          tasa_crecimiento_monto: kpisQuery.data?.tasa_crecimiento ?? 0,
          match_semantico_promedio: FALLBACK_KPIS.match_semantico_promedio,
        }
      : FALLBACK_KPIS;

  return {
    kpis,
    monthlyData: monthlyQuery.data || (scoped ? [] : FALLBACK_MONTHLY),
    suppliersData: suppliersQuery.data || (scoped ? [] : FALLBACK_SUPPLIERS),
    categoriesData: categoriesQuery.data || (scoped ? [] : FALLBACK_CATEGORIES),
    recentTenders: recentTendersQuery.data || (scoped ? [] : FALLBACK_RECENT_TENDERS),
    recentAwards: scoped ? [] : FALLBACK_RECENT_AWARDS,
    isLoading,
    isFetching,
    dataUpdatedAt: monthlyQuery.dataUpdatedAt,
    refetchAll,
  };
}
