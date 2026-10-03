import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { SystemStatus } from '@/types/ai';

export function useDataQuality() {
  const query = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get<SystemStatus>('/system/status'),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
  };
}
