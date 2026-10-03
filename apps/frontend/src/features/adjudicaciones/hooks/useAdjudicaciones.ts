import { useState, useCallback } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getSegmento } from '@/features/segmento';
import { api } from '@/lib/api';
import { preferredPageSize } from '@/features/auth/preferences';
import type { Adjudicacion, AdjudicacionFilters, OffsetPage } from '@/types';

export const FALLBACK_ADJUDICACIONES: Adjudicacion[] = [
  {
    id: 1,
    licitacion_id: 101,
    licitacion_codigo: '1057416-24-LE26',
    licitacion_nombre:
      'Adquisición de Camas Clínicas Eléctricas de 4 Secciones para Unidad de Geriatría',
    proveedor_id: 1,
    proveedor_rut: '76.432.189-5',
    proveedor_razon_social: 'Ortopedia y Equipos Médicos Austral SpA',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    monto_adjudicado: 128500000,
    fecha_adjudicacion: '2026-03-01',
    precio_unitario_promedio: 1420000,
    desviacion_precio_referencial: -6.5,
  },
  {
    id: 2,
    licitacion_id: 102,
    licitacion_codigo: '1057416-28-LP26',
    licitacion_nombre:
      'Suministro Bianual de Sillas de Ruedas Eléctricas y Manuales Pediátricas y Adulto',
    proveedor_id: 2,
    proveedor_rut: '77.892.450-1',
    proveedor_razon_social: 'Rehabilitación y Tecnología Médica Chile S.A.',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    monto_adjudicado: 89000000,
    fecha_adjudicacion: '2026-02-28',
    precio_unitario_promedio: 850000,
    desviacion_precio_referencial: -4.2,
  },
  {
    id: 3,
    licitacion_id: 103,
    licitacion_codigo: '721-33-LE26',
    licitacion_nombre: 'Grúas Eléctricas de Transferencia y Arnés Bariátrico',
    proveedor_id: 7,
    proveedor_rut: '77.304.812-9',
    proveedor_razon_social: 'Ergonomía Médica & Cuidados Intensivos SpA',
    organismo_id: 7,
    organismo_nombre: 'Servicio de Salud Metropolitano Central',
    monto_adjudicado: 45000000,
    fecha_adjudicacion: '2026-02-15',
    precio_unitario_promedio: 2250000,
    desviacion_precio_referencial: -8.0,
  },
  {
    id: 4,
    licitacion_id: 104,
    licitacion_codigo: '2234-15-LE26',
    licitacion_nombre: 'Adquisición de Sillas de Ruedas Bariátricas para Centros ELEAM',
    proveedor_id: 1,
    proveedor_rut: '76.432.189-5',
    proveedor_razon_social: 'Ortopedia y Equipos Médicos Austral SpA',
    organismo_id: 4,
    organismo_nombre: 'Instituto Nacional de Geriatría Pdte. Eduardo Frei Montalva',
    monto_adjudicado: 74500000,
    fecha_adjudicacion: '2026-02-10',
    precio_unitario_promedio: 1100000,
    desviacion_precio_referencial: -3.5,
  },
  {
    id: 5,
    licitacion_id: 105,
    licitacion_codigo: '1057416-31-LE26',
    licitacion_nombre: 'Reposición de Colchones Neumáticos con Presión Alternante Dinámica',
    proveedor_id: 3,
    proveedor_rut: '96.812.330-K',
    proveedor_razon_social: 'Insumos Clínicos Hospitalarios del Sur Ltda.',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    monto_adjudicado: 42000000,
    fecha_adjudicacion: '2026-01-30',
    precio_unitario_promedio: 350000,
    desviacion_precio_referencial: -5.0,
  },
  {
    id: 6,
    licitacion_id: 106,
    licitacion_codigo: '3310-8-LP26',
    licitacion_nombre: 'Equipamiento de Terapia Ocupacional y Adaptaciones Domiciliarias',
    proveedor_id: 4,
    proveedor_rut: '76.991.124-3',
    proveedor_razon_social: 'Movilidad Asistida y Ayudas Técnicas SpA',
    organismo_id: 3,
    organismo_nombre: 'Complejo Asistencial Dr. Sótero del Río',
    monto_adjudicado: 58000000,
    fecha_adjudicacion: '2026-01-22',
    precio_unitario_promedio: 580000,
    desviacion_precio_referencial: -2.8,
  },
  {
    id: 7,
    licitacion_id: 107,
    licitacion_codigo: '1057416-35-LR26',
    licitacion_nombre: 'Grúas Hospitalarias Móviles para Pacientes de Alta Dependencia',
    proveedor_id: 7,
    proveedor_rut: '77.304.812-9',
    proveedor_razon_social: 'Ergonomía Médica & Cuidados Intensivos SpA',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    monto_adjudicado: 64000000,
    fecha_adjudicacion: '2026-01-25',
    precio_unitario_promedio: 2400000,
    desviacion_precio_referencial: -7.2,
  },
  {
    id: 8,
    licitacion_id: 108,
    licitacion_codigo: '4102-18-LP26',
    licitacion_nombre:
      'Dotación Anual de Andadores Plegables con Ruedas y Asiento para Adulto Mayor',
    proveedor_id: 5,
    proveedor_rut: '78.112.980-8',
    proveedor_razon_social: 'Soluciones Geriátricas Integrales Chile Ltda.',
    organismo_id: 5,
    organismo_nombre: 'Hospital Las Higueras de Talcahuano',
    monto_adjudicado: 36000000,
    fecha_adjudicacion: '2026-01-15',
    precio_unitario_promedio: 120000,
    desviacion_precio_referencial: -4.0,
  },
];

export type AdjudicacionSortField =
  'monto_adjudicado' | 'fecha_adjudicacion' | 'proveedor_razon_social' | 'organismo_nombre';
export type SortDirection = 'asc' | 'desc';

export const ADJUDICACION_PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

/** Offline demo path: only used when the API is unreachable and no rubro is selected. */
function fallbackPage(
  filters: AdjudicacionFilters,
  sortField: AdjudicacionSortField,
  sortDirection: SortDirection,
  offset: number,
  limit: number,
): OffsetPage<Adjudicacion> {
  let items = [...FALLBACK_ADJUDICACIONES];
  if (filters.q) {
    const qLower = filters.q.toLowerCase();
    items = items.filter(
      (a) =>
        a.licitacion_codigo.toLowerCase().includes(qLower) ||
        a.licitacion_nombre.toLowerCase().includes(qLower) ||
        a.proveedor_razon_social.toLowerCase().includes(qLower) ||
        a.proveedor_rut.toLowerCase().includes(qLower) ||
        a.organismo_nombre.toLowerCase().includes(qLower),
    );
  }
  if (filters.monto_min !== undefined) {
    items = items.filter((a) => a.monto_adjudicado >= (filters.monto_min || 0));
  }
  items.sort((a, b) => {
    let aVal = a[sortField] ?? 0;
    let bVal = b[sortField] ?? 0;
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });
  return { data: items.slice(offset, offset + limit), total: items.length, offset, limit };
}

/**
 * Real awards from `/adjudicaciones` (core.adjudicacion): search, amount filter, sorting
 * and pagination all run in the API over every award.
 */
export function useAdjudicaciones(initialFilters?: AdjudicacionFilters) {
  const [filters, setFiltersState] = useState<AdjudicacionFilters>(initialFilters || {});
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSizeState] = useState<number>(() => preferredPageSize());
  const [sortField, setSortField] = useState<AdjudicacionSortField>('fecha_adjudicacion');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const params = {
    limit: pageSize,
    offset: (page - 1) * pageSize,
    sort_by: sortField,
    sort_dir: sortDirection,
    q: filters.q?.trim() || undefined,
    monto_min: filters.monto_min,
  };

  const query = useQuery({
    queryKey: ['adjudicaciones', params],
    queryFn: async (): Promise<OffsetPage<Adjudicacion>> => {
      try {
        return await api.get<OffsetPage<Adjudicacion>>('/adjudicaciones', { params });
      } catch (err) {
        if (getSegmento()) throw err;
        console.warn('API /adjudicaciones returned error, using fallback dataset:', err);
        return fallbackPage(filters, sortField, sortDirection, params.offset, params.limit);
      }
    },
    placeholderData: keepPreviousData,
    staleTime: 3 * 60 * 1000,
  });

  const items = query.data?.data ?? [];
  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const setFilters = useCallback((newFilters: Partial<AdjudicacionFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState({});
    setPage(1);
  }, []);

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    setPage(1);
  }, []);

  const setSort = useCallback((field: AdjudicacionSortField, direction: SortDirection = 'desc') => {
    setSortField(field);
    setSortDirection(direction);
    setPage(1);
  }, []);

  const toggleSort = (field: AdjudicacionSortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(
        field === 'proveedor_razon_social' || field === 'organismo_nombre' ? 'asc' : 'desc',
      );
    }
    setPage(1);
  };

  return {
    data: items,
    allItems: items,
    total,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    refetch: query.refetch,
    filters,
    setFilters,
    resetFilters,
    sortField,
    sortDirection,
    setSort,
    toggleSort,
  };
}
