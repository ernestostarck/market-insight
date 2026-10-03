import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  OrganismosTable,
  FALLBACK_ORGANISMOS,
} from '@/features/organismos';
import { OrganismosPage } from '@/pages/OrganismosPage';
import { OrganismoDetailPage } from '@/pages/OrganismoDetailPage';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Organismos Compradores & Categorías UNSPSC Modules', () => {
  describe('OrganismosTable', () => {
    it('renders agency rows with RUT, sector, region, and formatted CLP budget', () => {
      render(
        <MemoryRouter>
          <OrganismosTable items={FALLBACK_ORGANISMOS.slice(0, 3)} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Hospital San Juan de Dios')).toBeInTheDocument();
      expect(screen.getByText('61.602.040-3')).toBeInTheDocument();
      expect(screen.getByText('ORG-6932', { exact: false })).toBeInTheDocument();
      expect(screen.getByText(/\$3\.850\.000\.000/)).toBeInTheDocument();
      expect(screen.getByText('34 días')).toBeInTheDocument();
      expect(
        screen.getByText('Central de Abastecimiento del SNSS (CENABAST)'),
      ).toBeInTheDocument();
    });

    it('triggers sort callback when clicking table header', () => {
      const onSort = vi.fn();
      render(
        <MemoryRouter>
          <OrganismosTable items={FALLBACK_ORGANISMOS.slice(0, 2)} onSort={onSort} />
        </MemoryRouter>,
      );

      const budgetSortBtn = screen.getByText('Total Comprado (CLP)');
      fireEvent.click(budgetSortBtn);
      expect(onSort).toHaveBeenCalledWith('monto_total_comprado');
    });
  });

  describe('OrganismosPage', () => {
    it('renders organisms directory and filters by text query', async () => {
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <OrganismosPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(screen.getByText('Organismos Compradores')).toBeInTheDocument();
      expect(
        await screen.findByText('Hospital San Juan de Dios'),
      ).toBeInTheDocument();

      const searchInput = screen.getByPlaceholderText(/Buscar por Institución, RUT/i);
      fireEvent.change(searchInput, { target: { value: 'CENABAST' } });

      await waitFor(() => {
        expect(
          screen.getByText('Central de Abastecimiento del SNSS (CENABAST)'),
        ).toBeInTheDocument();
        expect(screen.queryByText('Hospital Dr. Gustavo Fricke')).not.toBeInTheDocument();
      });
    });
  });

  describe('OrganismoDetailPage', () => {
    it('renders agency executive profile with 4 KPI cards and sections', async () => {
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/organismos/1']}>
            <Routes>
              <Route path="/organismos/:id" element={<OrganismoDetailPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByText('Hospital San Juan de Dios'),
      ).toBeInTheDocument();

      // Check RUT
      expect(screen.getByText(/61\.602\.040-3/)).toBeInTheDocument();

      // Check 4 KPIs exist
      expect(screen.getByText('Gasto Total Comprado')).toBeInTheDocument();
      expect(screen.getByText('Licitaciones Totales')).toBeInTheDocument();
      expect(screen.getByText('Proveedores Contratados')).toBeInTheDocument();
      expect(screen.getByText('Plazo Promedio de Pago')).toBeInTheDocument();

      // Check sections
      expect(screen.getByText('Ranking de Proveedores Más Contratados')).toBeInTheDocument();
      expect(screen.getByText('Desglose de Compras por Rubro')).toBeInTheDocument();
      expect(screen.getByText('Licitaciones Recientes de este Organismo')).toBeInTheDocument();
    });
  });
});
