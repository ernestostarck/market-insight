import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { SearchEntity, SearchResult } from '@/types';

export const SUGGESTED_CONCEPTS = [
  'camas clínicas eléctricas',
  'sillas de ruedas bariátricas',
  'grúas de transferencia',
  'colchones antiescaras',
  'CENABAST',
  'Hospital San Juan de Dios',
  'Ortopedia y Equipos Médicos Austral',
  'rehabilitación motora',
  'dispositivos médicos certificados ISP',
];

export function useSearch(initialQuery = '') {
  const [query, setQuery] = useState<string>(initialQuery);
  const [selectedEntities, setSelectedEntities] = useState<SearchEntity[]>([
    'licitacion',
    'proveedor',
    'organismo',
  ]);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  const trimmedQuery = query.trim();

  const searchQuery = useQuery({
    queryKey: ['search', trimmedQuery, selectedEntities],
    queryFn: async (): Promise<SearchResult[]> => {
      if (trimmedQuery.length < 2) {
        // The API requires q.length >= 2; show nothing rather than fabricated highlights.
        return [];
      }

      const response = await api.get<{
        results: SearchResult[];
        total: number;
      }>('/search', {
        params: {
          q: trimmedQuery,
          entity: selectedEntities,
          limit_per_entity: 15,
        },
      });

      return response.results;
    },
    staleTime: 1000 * 60,
  });

  const toggleEntity = useCallback((entity: SearchEntity) => {
    setSelectedEntities((prev) => {
      if (prev.includes(entity)) {
        if (prev.length === 1) return prev; // Keep at least one
        return prev.filter((e) => e !== entity);
      } else {
        return [...prev, entity];
      }
    });
    setPage(1);
  }, []);

  const paginatedResults = useMemo(() => {
    const results = searchQuery.data || [];
    const startIndex = (page - 1) * pageSize;
    return results.slice(startIndex, startIndex + pageSize);
  }, [searchQuery.data, page, pageSize]);

  const totalResults = searchQuery.data?.length || 0;
  const totalPages = Math.max(1, Math.ceil(totalResults / pageSize));

  return {
    query,
    setQuery: (val: string) => {
      setQuery(val);
      setPage(1);
    },
    selectedEntities,
    toggleEntity,
    setSelectedEntities,
    results: paginatedResults,
    allResults: searchQuery.data || [],
    totalResults,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    isLoading: searchQuery.isLoading,
    isFetching: searchQuery.isFetching,
    refetch: searchQuery.refetch,
    conceptSuggestions: SUGGESTED_CONCEPTS,
  };
}
