import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  AIFilters,
  AIReviewAcceptAction,
  AIReviewModifyAction,
  AIReviewQueueItem,
  AIReviewStats,
} from '@/types/ai';

interface ReviewQueueResponse {
  total: number;
  items: AIReviewQueueItem[];
}

export function useAIDocuments(onlyUnreviewed: boolean) {
  const [filters, setFiltersState] = useState<AIFilters>({});
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['ai-review-queue', onlyUnreviewed],
    queryFn: async (): Promise<AIReviewQueueItem[]> => {
      const response = await api.get<ReviewQueueResponse>('/ai/reviews', {
        params: { only_unreviewed: onlyUnreviewed, limit: 100 },
      });
      return response.items;
    },
    staleTime: 60 * 1000,
  });

  const allDocuments = useMemo(() => query.data ?? [], [query.data]);

  const filteredDocuments = useMemo(() => {
    if (!filters.q) return allDocuments;
    const qLower = filters.q.toLowerCase();
    return allDocuments.filter(
      (d) =>
        (d.licitacion_codigo && d.licitacion_codigo.toLowerCase().includes(qLower)) ||
        (d.title && d.title.toLowerCase().includes(qLower)) ||
        (d.organismo && d.organismo.toLowerCase().includes(qLower)) ||
        (d.category_code && d.category_code.toLowerCase().includes(qLower)),
    );
  }, [allDocuments, filters.q]);

  const pendingReviewCount = useMemo(
    () => allDocuments.filter((d) => d.needs_review).length,
    [allDocuments],
  );

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['ai-review-queue'] });

  const acceptMutation = useMutation({
    mutationFn: (action: AIReviewAcceptAction) =>
      api.post(`/ai/reviews/${action.classificationId}/accept`, { reason: action.reason }),
    onSuccess: invalidate,
  });

  const modifyMutation = useMutation({
    mutationFn: (action: AIReviewModifyAction) =>
      api.post(`/ai/reviews/${action.classificationId}/modify`, {
        category_code: action.categoryCode,
        subcategory_code: action.subcategoryCode,
        relevant: action.relevant ?? true,
        relevance_tier: action.relevanceTier,
        reason: action.reason,
      }),
    onSuccess: invalidate,
  });

  const setFilters = useCallback((newFilters: Partial<AIFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState({});
  }, []);

  return {
    documents: filteredDocuments,
    allDocuments,
    pendingReviewCount,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    refetch: query.refetch,
    filters,
    setFilters,
    resetFilters,
    acceptReview: acceptMutation.mutateAsync,
    modifyReview: modifyMutation.mutateAsync,
  };
}

export function useAIReviewStats() {
  return useQuery({
    queryKey: ['ai-review-stats'],
    queryFn: async () => {
      const response = await api.get<{ stats: AIReviewStats }>('/ai/reviews/stats');
      return response.stats;
    },
    staleTime: 60 * 1000,
  });
}
