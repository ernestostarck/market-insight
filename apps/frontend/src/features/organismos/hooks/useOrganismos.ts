import { useState, useCallback } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { preferredPageSize } from '@/features/auth/preferences';
import { getSegmento } from '@/features/segmento';
import type { OffsetPage, Organismo, OrganismoFilters } from '@/types';

export const FALLBACK_ORGANISMOS: Organismo[] = [
  {
    id: 1,
    codigo: 'ORG-6932',
    nombre: 'Hospital San Juan de Dios',
    rut: '61.602.040-3',
    region: 'Metropolitana de Santiago',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 142,
    licitaciones_activas: 12,
    monto_total_comprado: 3850000000,
    dias_pago_promedio: 34,
    categoria_principal: 'Equipos Médicos y Camas Clínicas',
  },
  {
    id: 2,
    codigo: 'ORG-1024',
    nombre: 'Central de Abastecimiento del SNSS (CENABAST)',
    rut: '61.608.000-7',
    region: 'Metropolitana de Santiago',
    sector: 'Central de Abastecimiento',
    total_licitaciones: 320,
    licitaciones_activas: 28,
    monto_total_comprado: 12400000000,
    dias_pago_promedio: 26,
    categoria_principal: 'Insumos Clínicos y Ayudas Técnicas',
  },
  {
    id: 3,
    codigo: 'ORG-5512',
    nombre: 'Complejo Asistencial Dr. Sótero del Río',
    rut: '61.602.120-5',
    region: 'Metropolitana de Santiago',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 118,
    licitaciones_activas: 9,
    monto_total_comprado: 2950000000,
    dias_pago_promedio: 42,
    categoria_principal: 'Movilidad y Sillas de Ruedas',
  },
  {
    id: 4,
    codigo: 'ORG-8840',
    nombre: 'Instituto Nacional de Geriatría Pdte. Eduardo Frei Montalva',
    rut: '61.602.400-K',
    region: 'Metropolitana de Santiago',
    sector: 'Institutos Especializados',
    total_licitaciones: 64,
    licitaciones_activas: 5,
    monto_total_comprado: 1280000000,
    dias_pago_promedio: 29,
    categoria_principal: 'Mobiliario Clínico Geriátrico',
  },
  {
    id: 5,
    codigo: 'ORG-3341',
    nombre: 'Hospital Las Higueras de Talcahuano',
    rut: '61.603.200-2',
    region: 'Biobío',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 86,
    licitaciones_activas: 7,
    monto_total_comprado: 1980000000,
    dias_pago_promedio: 38,
    categoria_principal: 'Equipos Médicos y Camas Clínicas',
  },
  {
    id: 6,
    codigo: 'ORG-4109',
    nombre: 'Hospital Regional Dr. Guillermo Grant Benavente',
    rut: '61.603.010-7',
    region: 'Biobío',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 156,
    licitaciones_activas: 14,
    monto_total_comprado: 4120000000,
    dias_pago_promedio: 45,
    categoria_principal: 'Equipos Médicos y Camas Clínicas',
  },
  {
    id: 7,
    codigo: 'ORG-7721',
    nombre: 'Servicio de Salud Metropolitano Central',
    rut: '61.602.000-4',
    region: 'Metropolitana de Santiago',
    sector: 'Servicios de Salud',
    total_licitaciones: 98,
    licitaciones_activas: 8,
    monto_total_comprado: 2340000000,
    dias_pago_promedio: 32,
    categoria_principal: 'Grúas y Transferencia',
  },
  {
    id: 8,
    codigo: 'ORG-9014',
    nombre: 'Hospital Dr. Gustavo Fricke',
    rut: '61.604.100-1',
    region: 'Valparaíso',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 104,
    licitaciones_activas: 11,
    monto_total_comprado: 2650000000,
    dias_pago_promedio: 36,
    categoria_principal: 'Movilidad y Sillas de Ruedas',
  },
  {
    id: 9,
    codigo: 'ORG-2150',
    nombre: 'Hospital Regional de Antofagasta Dr. Leonardo Guzmán',
    rut: '61.605.300-K',
    region: 'Antofagasta',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 78,
    licitaciones_activas: 6,
    monto_total_comprado: 1840000000,
    dias_pago_promedio: 40,
    categoria_principal: 'Equipos Médicos y Camas Clínicas',
  },
  {
    id: 10,
    codigo: 'ORG-6320',
    nombre: 'Hospital Clínico de Magallanes Dr. Lautaro Navarro',
    rut: '61.606.400-8',
    region: 'Magallanes y de la Antártica Chilena',
    sector: 'Hospitales Autogestionados',
    total_licitaciones: 52,
    licitaciones_activas: 4,
    monto_total_comprado: 1120000000,
    dias_pago_promedio: 48,
    categoria_principal: 'Insumos Clínicos y Ayudas Técnicas',
  },
];

export type OrganismoSortField =
  'monto_total_comprado' | 'total_licitaciones' | 'licitaciones_activas' | 'nombre';
export type SortDirection = 'asc' | 'desc';

export const ORGANISMO_PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

/** Offline demo path: only used when the API is unreachable and no rubro is selected. */
function fallbackPage(
  q: string | undefined,
  sortField: OrganismoSortField,
  sortDirection: SortDirection,
  offset: number,
  limit: number,
): OffsetPage<Organismo> {
  let items = [...FALLBACK_ORGANISMOS];
  if (q) {
    const qLower = q.toLowerCase();
    items = items.filter(
      (o) =>
        o.nombre?.toLowerCase().includes(qLower) ||
        o.codigo?.toLowerCase().includes(qLower) ||
        o.rut?.toLowerCase().includes(qLower),
    );
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
 * Server-side ranking of buying agencies (`/organismos/ranking`): search, sorting and
 * pagination run in the API over every agency, with real purchasing stats.
 */
export function useOrganismos(initialFilters?: OrganismoFilters) {
  const [filters, setFiltersState] = useState<OrganismoFilters>(initialFilters || {});
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSizeState] = useState<number>(() => preferredPageSize());
  const [sortField, setSortField] = useState<OrganismoSortField>('monto_total_comprado');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const params = {
    limit: pageSize,
    offset: (page - 1) * pageSize,
    sort_by: sortField,
    sort_dir: sortDirection,
    q: filters.q?.trim() || undefined,
  };

  const query = useQuery({
    queryKey: ['organismos', 'ranking', params],
    queryFn: async (): Promise<OffsetPage<Organismo>> => {
      try {
        return await api.get<OffsetPage<Organismo>>('/organismos/ranking', { params });
      } catch (err) {
        if (getSegmento()) throw err;
        console.warn('API /organismos/ranking returned error, using fallback dataset:', err);
        return fallbackPage(params.q, sortField, sortDirection, params.offset, params.limit);
      }
    },
    placeholderData: keepPreviousData,
    staleTime: 3 * 60 * 1000,
  });

  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const items = query.data?.data ?? [];

  const setFilters = useCallback((newFilters: Partial<OrganismoFilters>) => {
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

  const setSort = useCallback((field: OrganismoSortField, direction: SortDirection = 'desc') => {
    setSortField(field);
    setSortDirection(direction);
    setPage(1);
  }, []);

  const toggleSort = (field: OrganismoSortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'nombre' ? 'asc' : 'desc');
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
