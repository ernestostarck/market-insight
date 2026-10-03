import { useState, useCallback } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { preferredPageSize } from '@/features/auth/preferences';
import type { Categoria, CategoriaDetail, CategoriaFilters, OffsetPage } from '@/types';

export type CategoriaSortField =
  'monto_total' | 'total_licitaciones' | 'total_proveedores' | 'codigo' | 'nombre';
export type SortDirection = 'asc' | 'desc';

export const CATEGORIA_PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

export function useCategorias(initialFilters?: CategoriaFilters) {
  const [filters, setFiltersState] = useState<CategoriaFilters>(initialFilters || {});
  const [sortField, setSortField] = useState<CategoriaSortField>('monto_total');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [selectedCategoriaId, setSelectedCategoriaId] = useState<number | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSizeState] = useState<number>(() => preferredPageSize());

  // Real core.categoria rows with award stats, ranked and paginated by the backend
  // (`/categorias/ranking`) — no fallback dataset: if the API fails, the error surfaces.
  const params = {
    limit: pageSize,
    offset: (page - 1) * pageSize,
    sort_by: sortField,
    sort_dir: sortDirection,
    q: filters.q?.trim() || undefined,
    monto_minimo: filters.monto_minimo,
  };

  const query = useQuery({
    queryKey: ['categorias', 'ranking', params],
    queryFn: () => api.get<OffsetPage<Categoria>>('/categorias/ranking', { params }),
    placeholderData: keepPreviousData,
    staleTime: 3 * 60 * 1000,
  });

  const items = query.data?.data ?? [];
  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const detailQuery = useQuery({
    queryKey: ['categoria-detail', selectedCategoriaId],
    queryFn: async (): Promise<CategoriaDetail> =>
      api.get<CategoriaDetail>(`/categorias/${selectedCategoriaId}`),
    enabled: selectedCategoriaId !== null,
    staleTime: 3 * 60 * 1000,
  });

  const setFilters = useCallback((newFilters: Partial<CategoriaFilters>) => {
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

  const setSort = useCallback((field: CategoriaSortField, direction: SortDirection = 'desc') => {
    setSortField(field);
    setSortDirection(direction);
    setPage(1);
  }, []);

  const toggleSort = (field: CategoriaSortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'codigo' || field === 'nombre' ? 'asc' : 'desc');
    }
    setPage(1);
  };

  const openCategoriaDetail = (cat: Categoria) => setSelectedCategoriaId(cat.id);
  const closeCategoriaDetail = () => setSelectedCategoriaId(null);

  return {
    items,
    total,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    setSort,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    filters,
    setFilters,
    resetFilters,
    sortField,
    sortDirection,
    toggleSort,
    selectedCategoria: detailQuery.data ?? null,
    isDetailLoading: detailQuery.isLoading,
    openCategoriaDetail,
    closeCategoriaDetail,
  };
}
