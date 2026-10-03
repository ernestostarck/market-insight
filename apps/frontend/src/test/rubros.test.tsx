import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { api } from '@/lib/api';
import { RubrosPage } from '@/pages/RubrosPage';
import { FALLBACK_TAXONOMIA } from '@/features/taxonomia';
import { getSegmento, setSegmento } from '@/features/segmento';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn() },
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/rubros']}>
        <Routes>
          <Route path="/rubros" element={<RubrosPage />} />
          <Route path="/mercado" element={<p>Vista de mercado</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RubrosPage', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
    setSegmento(null);
  });

  it('lists every sector from the API, including Vestuario', async () => {
    vi.mocked(api.get).mockResolvedValue(FALLBACK_TAXONOMIA);
    renderPage();

    await waitFor(() => expect(screen.getByText('Vestuario')).toBeInTheDocument());
    expect(screen.getByText('Salud')).toBeInTheDocument();
    expect(screen.getByText('Nuevo')).toBeInTheDocument();
  });

  it('expands Vestuario to reveal the shapewear concepts on click', async () => {
    vi.mocked(api.get).mockResolvedValue(FALLBACK_TAXONOMIA);
    renderPage();

    const vestuario = await screen.findByText('Vestuario');
    fireEvent.click(vestuario);

    expect(await screen.findByText('Vestimenta moldeadora')).toBeInTheDocument();
    expect(screen.getByText('Faja moldeadora tipo short')).toBeInTheDocument();
    expect(screen.getByText('Faja moldeadora tipo colaless')).toBeInTheDocument();
  });

  it('selecting a rubro scopes the platform to it and opens the market view', async () => {
    vi.mocked(api.get).mockResolvedValue(FALLBACK_TAXONOMIA);
    renderPage();

    await screen.findByText('Vestuario');
    // Vestuario is the last category in the taxonomy.
    const buttons = screen.getAllByRole('button', { name: 'Analizar rubro' });
    fireEvent.click(buttons[buttons.length - 1]);

    expect(getSegmento()).toEqual({ code: 'cat:apparel', label: 'Vestuario' });
    expect(await screen.findByText('Vista de mercado')).toBeInTheDocument();
  });

  it('selecting a concept chip scopes the platform to that concept', async () => {
    vi.mocked(api.get).mockResolvedValue(FALLBACK_TAXONOMIA);
    renderPage();

    fireEvent.click(await screen.findByText('Vestuario'));
    fireEvent.click(await screen.findByRole('button', { name: 'Faja reductora' }));

    expect(getSegmento()).toEqual({
      code: 'concept:faja_reductora',
      label: 'Faja reductora',
      parentLabel: 'Vestuario',
    });
  });

  it('falls back to the offline taxonomy (still including Vestuario) if the API fails', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network error'));
    renderPage();

    await waitFor(() => expect(screen.getByText('Vestuario')).toBeInTheDocument());
  });
});
