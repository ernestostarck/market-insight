import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { api } from '@/lib/api';
import { useProveedores, FALLBACK_PROVEEDORES } from '@/features/proveedores';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn() },
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

/** Params of the most recent /proveedores/ranking call. */
function lastParams() {
  const calls = vi.mocked(api.get).mock.calls;
  const [url, config] = calls[calls.length - 1];
  expect(url).toBe('/proveedores/ranking');
  return (config as { params: Record<string, unknown> }).params;
}

describe('useProveedores (server-side ranking)', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
    vi.mocked(api.get).mockResolvedValue({
      data: FALLBACK_PROVEEDORES.slice(0, 10),
      total: 3146,
      offset: 0,
      limit: 10,
    });
  });

  it('requests the top 10 by awarded amount by default and uses the API total', async () => {
    const { result } = renderHook(() => useProveedores(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(lastParams()).toMatchObject({
      limit: 10,
      offset: 0,
      sort_by: 'monto_total_adjudicado',
      sort_dir: 'desc',
    });
    expect(result.current.total).toBe(3146);
    expect(result.current.totalPages).toBe(315);
  });

  it('changing the page size asks the server for the top N and resets to page 1', async () => {
    const { result } = renderHook(() => useProveedores(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setPage(3));
    await waitFor(() => expect(lastParams()).toMatchObject({ offset: 20 }));

    act(() => result.current.setPageSize(25));
    await waitFor(() => expect(lastParams()).toMatchObject({ limit: 25, offset: 0 }));
    expect(result.current.page).toBe(1);
  });

  it('sends search and rubro filters to the API, ignoring the "all" placeholder', async () => {
    const { result } = renderHook(() => useProveedores(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setFilters({ q: ' ortopedia ', rubro: 'all' }));
    await waitFor(() => expect(lastParams()).toMatchObject({ q: 'ortopedia' }));
    expect(lastParams().rubro).toBeUndefined();

    act(() => result.current.setFilters({ rubro: 'Equipos médicos' }));
    await waitFor(() => expect(lastParams()).toMatchObject({ rubro: 'Equipos médicos' }));
  });

  it('sorting is delegated to the server', async () => {
    const { result } = renderHook(() => useProveedores(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.toggleSort('razon_social'));
    await waitFor(() =>
      expect(lastParams()).toMatchObject({ sort_by: 'razon_social', sort_dir: 'asc' }),
    );
  });
});
