import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { OrdenDeCompra, OrdenDeCompraFilters } from '@/types';
import type { SortDirection } from './useAdjudicaciones';

export const FALLBACK_ORDENES_COMPRA: OrdenDeCompra[] = [
  {
    id: 1,
    codigo: '1057416-24-OC1',
    nombre: 'Orden de Compra - 20 Camas Clínicas Eléctricas y Colchones',
    estado: 'Aceptada',
    monto_total: 64250000,
    moneda: 'CLP',
    fecha_creacion: '2026-03-05',
    fecha_envio: '2026-03-06',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    proveedor_id: 1,
    proveedor_nombre: 'Ortopedia y Equipos Médicos Austral SpA',
    proveedor_rut: '76.432.189-5',
    licitacion_id: 101,
    licitacion_codigo: '1057416-24-LE26',
    items_count: 20,
  },
  {
    id: 2,
    codigo: '1057416-24-OC2',
    nombre: 'Orden de Compra - Sillas de Ruedas Bariátricas Reforzadas',
    estado: 'Recepcionada',
    monto_total: 44500000,
    moneda: 'CLP',
    fecha_creacion: '2026-03-02',
    fecha_envio: '2026-03-03',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    proveedor_id: 2,
    proveedor_nombre: 'Rehabilitación y Tecnología Médica Chile S.A.',
    proveedor_rut: '77.892.450-1',
    licitacion_id: 102,
    licitacion_codigo: '1057416-28-LP26',
    items_count: 50,
  },
  {
    id: 3,
    codigo: '721-33-OC1',
    nombre: 'Orden de Compra - Grúas de Pacientes y Arneses Clínicos',
    estado: 'Facturada',
    monto_total: 45000000,
    moneda: 'CLP',
    fecha_creacion: '2026-02-20',
    fecha_envio: '2026-02-21',
    organismo_id: 7,
    organismo_nombre: 'Servicio de Salud Metropolitano Central',
    proveedor_id: 7,
    proveedor_nombre: 'Ergonomía Médica & Cuidados Intensivos SpA',
    proveedor_rut: '77.304.812-9',
    licitacion_id: 103,
    licitacion_codigo: '721-33-LE26',
    items_count: 20,
  },
  {
    id: 4,
    codigo: '2234-15-OC1',
    nombre: 'Orden de Compra - Sillas Neurológicas Basculantes para ELEAM',
    estado: 'Pagada',
    monto_total: 74500000,
    moneda: 'CLP',
    fecha_creacion: '2026-02-14',
    fecha_envio: '2026-02-15',
    organismo_id: 4,
    organismo_nombre: 'Instituto Nacional de Geriatría Pdte. Eduardo Frei Montalva',
    proveedor_id: 1,
    proveedor_nombre: 'Ortopedia y Equipos Médicos Austral SpA',
    proveedor_rut: '76.432.189-5',
    licitacion_id: 104,
    licitacion_codigo: '2234-15-LE26',
    items_count: 65,
  },
  {
    id: 5,
    codigo: '1057416-31-OC1',
    nombre: 'Orden de Compra - Colchones Antiescaras con Compresor Silencioso',
    estado: 'Aceptada',
    monto_total: 42000000,
    moneda: 'CLP',
    fecha_creacion: '2026-02-04',
    fecha_envio: '2026-02-05',
    organismo_id: 1,
    organismo_nombre: 'Hospital San Juan de Dios',
    proveedor_id: 3,
    proveedor_nombre: 'Insumos Clínicos Hospitalarios del Sur Ltda.',
    proveedor_rut: '96.812.330-K',
    licitacion_id: 105,
    licitacion_codigo: '1057416-31-LE26',
    items_count: 120,
  },
  {
    id: 6,
    codigo: '3310-8-OC1',
    nombre: 'Orden de Compra - Rampas Telescópicas de Aluminio y Barras de Baño',
    estado: 'Recepcionada',
    monto_total: 58000000,
    moneda: 'CLP',
    fecha_creacion: '2026-01-28',
    fecha_envio: '2026-01-29',
    organismo_id: 3,
    organismo_nombre: 'Complejo Asistencial Dr. Sótero del Río',
    proveedor_id: 4,
    proveedor_nombre: 'Movilidad Asistida y Ayudas Técnicas SpA',
    proveedor_rut: '76.991.124-3',
    licitacion_id: 106,
    licitacion_codigo: '3310-8-LP26',
    items_count: 100,
  },
];

export type OrdenDeCompraSortField = 'monto_total' | 'fecha_creacion' | 'codigo';

export function useOrdenesCompra(initialFilters?: OrdenDeCompraFilters) {
  const [filters, setFiltersState] = useState<OrdenDeCompraFilters>(initialFilters || {});
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [sortField, setSortField] = useState<OrdenDeCompraSortField>('fecha_creacion');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const query = useQuery({
    queryKey: ['ordenes-compra', filters, sortField, sortDirection],
    queryFn: async (): Promise<OrdenDeCompra[]> => {
      const response = await api.get<{ data: OrdenDeCompra[] } | OrdenDeCompra[]>(
        '/ordenes-compra',
        {
          params: {
            q: filters.q,
            estado: filters.estado,
          },
        },
      );
      let items = Array.isArray(response) ? response : response.data;

      // The API does not yet filter/sort by these fields, so it's applied client-side.
      if (filters.q) {
        const qLower = filters.q.toLowerCase();
        items = items.filter(
          (o) =>
            o.codigo.toLowerCase().includes(qLower) ||
            (o.nombre && o.nombre.toLowerCase().includes(qLower)) ||
            (o.proveedor_nombre && o.proveedor_nombre.toLowerCase().includes(qLower)) ||
            (o.organismo_nombre && o.organismo_nombre.toLowerCase().includes(qLower)),
        );
      }

      if (filters.estado && filters.estado !== 'all') {
        items = items.filter((o) => o.estado?.toLowerCase() === filters.estado?.toLowerCase());
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

      return items;
    },
    staleTime: 3 * 60 * 1000,
  });

  const allItems = useMemo(() => query.data || [], [query.data]);
  const total = allItems.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const paginatedItems = useMemo(() => {
    const start = (page - 1) * pageSize;
    return allItems.slice(start, start + pageSize);
  }, [allItems, page, pageSize]);

  const setFilters = useCallback((newFilters: Partial<OrdenDeCompraFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState({});
    setPage(1);
  }, []);

  const toggleSort = (field: OrdenDeCompraSortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  return {
    data: paginatedItems,
    allItems,
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
    toggleSort,
  };
}
