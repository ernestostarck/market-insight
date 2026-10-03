import { useState, useCallback } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { preferredPageSize } from '@/features/auth/preferences';
import type { FacetCount, OffsetPage, Proveedor, ProveedorFilters } from '@/types';

export const FALLBACK_PROVEEDORES: Proveedor[] = [
  {
    id: 1,
    rut: '76.432.189-5',
    razon_social: 'Ortopedia y Equipos Médicos Austral SpA',
    nombre_fantasia: 'Ortopedia Austral',
    region: 'Metropolitana de Santiago',
    categoria_principal: 'Equipos Médicos y Camas Clínicas',
    fecha_registro: '2018-04-12',
    total_licitaciones_participadas: 54,
    total_adjudicaciones: 38,
    tasa_exito: 70.4,
    monto_total_adjudicado: 1420500000,
  },
  {
    id: 2,
    rut: '77.892.450-1',
    razon_social: 'Rehabilitación y Tecnología Médica Chile S.A.',
    nombre_fantasia: 'RehabTech Chile',
    region: 'Metropolitana de Santiago',
    categoria_principal: 'Movilidad y Sillas de Ruedas',
    fecha_registro: '2019-01-20',
    total_licitaciones_participadas: 48,
    total_adjudicaciones: 29,
    tasa_exito: 60.4,
    monto_total_adjudicado: 980200000,
  },
  {
    id: 3,
    rut: '96.812.330-K',
    razon_social: 'Insumos Clínicos Hospitalarios del Sur Ltda.',
    nombre_fantasia: 'InsuSur Clínico',
    region: 'Biobío',
    categoria_principal: 'Colchones Antiescaras e Insumos',
    fecha_registro: '2016-08-15',
    total_licitaciones_participadas: 42,
    total_adjudicaciones: 22,
    tasa_exito: 52.4,
    monto_total_adjudicado: 645000000,
  },
  {
    id: 4,
    rut: '76.991.124-3',
    razon_social: 'Movilidad Asistida y Ayudas Técnicas SpA',
    nombre_fantasia: 'Movilidad Asistida',
    region: 'Valparaíso',
    categoria_principal: 'Accesibilidad Universal y Rampas',
    fecha_registro: '2020-05-11',
    total_licitaciones_participadas: 31,
    total_adjudicaciones: 19,
    tasa_exito: 61.3,
    monto_total_adjudicado: 512000000,
  },
  {
    id: 5,
    rut: '78.112.980-8',
    razon_social: 'Soluciones Geriátricas Integrales Chile Ltda.',
    nombre_fantasia: 'GeriaChile',
    region: 'Metropolitana de Santiago',
    categoria_principal: 'Mobiliario Clínico Geriátrico',
    fecha_registro: '2017-11-04',
    total_licitaciones_participadas: 36,
    total_adjudicaciones: 24,
    tasa_exito: 66.7,
    monto_total_adjudicado: 430000000,
  },
  {
    id: 6,
    rut: '76.220.551-7',
    razon_social: 'Biomédica y Monitoreo Clínico Austral S.A.',
    nombre_fantasia: 'Biomédica Austral',
    region: 'Los Lagos',
    categoria_principal: 'Monitoreo y Diagnóstico',
    fecha_registro: '2021-02-18',
    total_licitaciones_participadas: 28,
    total_adjudicaciones: 14,
    tasa_exito: 50.0,
    monto_total_adjudicado: 380000000,
  },
  {
    id: 7,
    rut: '77.304.812-9',
    razon_social: 'Ergonomía Médica & Cuidados Intensivos SpA',
    nombre_fantasia: 'ErgoMed',
    region: 'Metropolitana de Santiago',
    categoria_principal: 'Grúas y Transferencia',
    fecha_registro: '2019-09-29',
    total_licitaciones_participadas: 25,
    total_adjudicaciones: 17,
    tasa_exito: 68.0,
    monto_total_adjudicado: 295000000,
  },
  {
    id: 8,
    rut: '96.503.210-4',
    razon_social: 'Equipamiento Quirúrgico y Hospitalario Central Ltda.',
    nombre_fantasia: 'EquipCentral',
    region: 'Antofagasta',
    categoria_principal: 'Equipos Médicos y Camas Clínicas',
    fecha_registro: '2015-06-22',
    total_licitaciones_participadas: 34,
    total_adjudicaciones: 18,
    tasa_exito: 52.9,
    monto_total_adjudicado: 360000000,
  },
];

export type ProveedorSortField =
  'monto_total_adjudicado' | 'total_adjudicaciones' | 'tasa_exito' | 'razon_social';
export type SortDirection = 'asc' | 'desc';

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

/**
 * Server-side ranking of proveedores (`/proveedores/ranking`): filtering, sorting and
 * pagination all happen in the API, so "top 10 by monto" really is the top 10 of all
 * suppliers, not of a client-side sample.
 */
export function useProveedores(initialFilters?: ProveedorFilters) {
  const [filters, setFiltersState] = useState<ProveedorFilters>(initialFilters || {});
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSizeState] = useState<number>(() => preferredPageSize());
  const [sortField, setSortField] = useState<ProveedorSortField>('monto_total_adjudicado');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const params = {
    limit: pageSize,
    offset: (page - 1) * pageSize,
    sort_by: sortField,
    sort_dir: sortDirection,
    q: filters.q?.trim() || undefined,
    rubro: filters.rubro && filters.rubro !== 'all' ? filters.rubro : undefined,
    tasa_minima: filters.tasa_minima,
  };

  const query = useQuery({
    queryKey: ['proveedores', 'ranking', params],
    queryFn: () => api.get<OffsetPage<Proveedor>>('/proveedores/ranking', { params }),
    placeholderData: keepPreviousData,
    staleTime: 3 * 60 * 1000,
  });

  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const setFilters = useCallback((newFilters: Partial<ProveedorFilters>) => {
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

  const setSort = useCallback((field: ProveedorSortField, direction: SortDirection = 'desc') => {
    setSortField(field);
    setSortDirection(direction);
    setPage(1);
  }, []);

  const toggleSort = (field: ProveedorSortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'razon_social' ? 'asc' : 'desc');
    }
    setPage(1);
  };

  const items = query.data?.data ?? [];

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
    isError: query.isError,
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

/** Real main-award categories (with supplier counts) for the rubro filter. */
export function useProveedorRubros() {
  return useQuery({
    queryKey: ['proveedores', 'rubros'],
    queryFn: () => api.get<FacetCount[]>('/proveedores/rubros'),
    staleTime: 10 * 60 * 1000,
  });
}
