import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CategoriasTable } from '@/features/categorias';
import { CategoriasPage } from '@/pages/CategoriasPage';
import type { Categoria, CategoriaDetail } from '@/types';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn() },
}));

function createTestQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

const SILLAS: Categoria = {
  id: 1,
  codigo: '42192200',
  nombre: 'Equipamiento médico / Movilidad asistida / Sillas de Ruedas',
  segmento: 'Equipamiento médico',
  familia: 'Movilidad asistida',
  clase: 'Sillas de Ruedas',
  total_licitaciones: 12,
  monto_total: 48_000_000,
  total_proveedores: 4,
  total_organismos: 3,
};

const VESTUARIO: Categoria = {
  id: 2,
  codigo: '53102500',
  nombre: 'Ropa, maletas y productos de aseo personal / Ropa / Vestuario',
  segmento: 'Ropa, maletas y productos de aseo personal',
  familia: 'Ropa',
  clase: 'Vestuario',
  total_licitaciones: 2,
  monto_total: 1_200_000,
  total_proveedores: 1,
  total_organismos: 1,
};

describe('CategoriasTable', () => {
  it('renders real core.categoria rows with their award stats, no level/growth columns', () => {
    render(
      <MemoryRouter>
        <CategoriasTable items={[SILLAS, VESTUARIO]} />
      </MemoryRouter>,
    );

    expect(screen.getByText('42192200')).toBeInTheDocument();
    expect(screen.getByText('Sillas de Ruedas')).toBeInTheDocument();
    expect(screen.getByText('Vestuario')).toBeInTheDocument();
    expect(screen.getByText('Equipamiento médico / Movilidad asistida')).toBeInTheDocument();
    expect(screen.queryByText('Segmento')).not.toBeInTheDocument();
    expect(screen.queryByText(/YoY/)).not.toBeInTheDocument();
  });
});

describe('CategoriasPage', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
  });

  it('renders rubros fetched from the real API', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [SILLAS, VESTUARIO],
      total: 2,
      offset: 0,
      limit: 10,
    });
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CategoriasPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('Sillas de Ruedas')).toBeInTheDocument();
    expect(screen.getByText('Vestuario')).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith(
      '/categorias/ranking',
      expect.objectContaining({ params: expect.any(Object) }),
    );
  });

  it('shows an honest error state instead of fabricated data when the API fails', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('network error'));
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CategoriasPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('No se pudo cargar los rubros')).toBeInTheDocument();
    expect(screen.queryByText('Sillas de Ruedas')).not.toBeInTheDocument();
  });

  it('opens the detail modal with real top suppliers and buyers from /categorias/{id}', async () => {
    const detail: CategoriaDetail = {
      ...SILLAS,
      principales_proveedores: [
        {
          proveedor_id: 10,
          proveedor_nombre: 'Ortopedia Austral',
          proveedor_rut: '76.123.456-7',
          monto_adjudicado: 30_000_000,
          cuota: 62.5,
        },
      ],
      principales_organismos: [
        {
          organismo_id: 20,
          organismo_nombre: 'Hospital San Juan de Dios',
          monto_comprado: 30_000_000,
          total_licitaciones: 5,
        },
      ],
    };
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/categorias/ranking') return { data: [SILLAS], total: 1, offset: 0, limit: 10 };
      if (url === '/categorias/1') return detail;
      throw new Error(`unexpected url ${url}`);
    });
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CategoriasPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(await screen.findByText('Sillas de Ruedas'));

    expect(await screen.findByText('Ortopedia Austral')).toBeInTheDocument();
    expect(screen.getByText('62.5%')).toBeInTheDocument();
    expect(screen.getByText('Hospital San Juan de Dios')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /cerrar/i }));
    await waitFor(() => expect(screen.queryByText('Ortopedia Austral')).not.toBeInTheDocument());
  });

  it('filters by search text against the real API', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [SILLAS], total: 1, offset: 0, limit: 10 });
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CategoriasPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText('Sillas de Ruedas');
    fireEvent.change(screen.getByPlaceholderText(/Buscar por código o nombre/i), {
      target: { value: 'vestuario' },
    });

    await waitFor(() =>
      expect(api.get).toHaveBeenLastCalledWith(
        '/categorias/ranking',
        expect.objectContaining({ params: expect.objectContaining({ q: 'vestuario' }) }),
      ),
    );
  });
});
