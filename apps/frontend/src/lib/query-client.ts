import { QueryClient } from '@tanstack/react-query';
import type { ApiError } from '@/types/common';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes fresh data
      gcTime: 1000 * 60 * 30, // 30 minutes in garbage collection cache
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      retry: (failureCount, error) => {
        // Do not retry on client auth errors (401, 403, 404)
        const apiError = error as unknown as ApiError;
        if (apiError?.status && [401, 403, 404].includes(apiError.status)) {
          return false;
        }
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
