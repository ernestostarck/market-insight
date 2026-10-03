import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SearchResultCard, SearchScoreBadge } from '@/features/search';
import {
  ProveedoresTable,
  ProveedorComparator,
  FALLBACK_PROVEEDORES,
} from '@/features/proveedores';
import { ProveedorDetailPage } from '@/pages/ProveedorDetailPage';
import type { SearchResult } from '@/types';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Search and Proveedores Modules', () => {
  describe('SearchScoreBadge', () => {
    it('renders formatted percentages for hybrid, semantic and keyword scores', () => {
      render(<SearchScoreBadge score={0.92} semanticScore={0.95} keywordScore={0.88} />);

      expect(screen.getByText('92% Match Híbrido')).toBeInTheDocument();
      expect(screen.getByText('Semántico: 95%')).toBeInTheDocument();
      expect(screen.getByText('Keyword: 88%')).toBeInTheDocument();
    });
  });

  describe('SearchResultCard', () => {
    const mockResult: SearchResult = {
      entity_type: 'licitacion',
      id: 101,
      title: 'Adquisición de Camas Clínicas Eléctricas',
      subtitle: 'Hospital San Juan de Dios • $128.500.000 CLP',
      code: '1057416-24-LE26',
      score: 0.94,
      semantic_score: 0.96,
      keyword_score: 0.91,
    };

    it('renders result with entity badge, code, title and action link', () => {
      render(
        <MemoryRouter>
          <SearchResultCard result={mockResult} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Licitación Pública')).toBeInTheDocument();
      expect(screen.getByText('1057416-24-LE26')).toBeInTheDocument();
      expect(screen.getByText('Adquisición de Camas Clínicas Eléctricas')).toBeInTheDocument();
      expect(screen.getByText('94% Match Híbrido')).toBeInTheDocument();

      const link = screen.getByRole('link', { name: /ver ficha/i });
      expect(link).toHaveAttribute('href', '/licitaciones/101');
    });

    it('renders proveedor entity type correctly', () => {
      const provResult: SearchResult = {
        entity_type: 'proveedor',
        id: 1,
        title: 'Ortopedia y Equipos Médicos Austral SpA',
        subtitle: 'RUT: 76.432.189-5 • Equipamiento Geriátrico',
        code: '76.432.189-5',
        score: 0.89,
      };

      render(
        <MemoryRouter>
          <SearchResultCard result={provResult} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Proveedor del Estado')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /ver ficha/i })).toHaveAttribute(
        'href',
        '/proveedores/1',
      );
    });
  });

  describe('ProveedoresTable', () => {
    it('renders supplier table rows with RUT, CLP amount and success rate', () => {
      render(
        <MemoryRouter>
          <ProveedoresTable items={FALLBACK_PROVEEDORES.slice(0, 2)} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Ortopedia y Equipos Médicos Austral SpA')).toBeInTheDocument();
      expect(screen.getByText('76.432.189-5')).toBeInTheDocument();
      expect(screen.getByText(/\$1\.420\.500\.000/)).toBeInTheDocument();
      expect(screen.getByText('70.4%')).toBeInTheDocument();
    });

    it('triggers sort callbacks on column header click', () => {
      const onSort = vi.fn();
      render(
        <MemoryRouter>
          <ProveedoresTable items={FALLBACK_PROVEEDORES.slice(0, 2)} onSort={onSort} />
        </MemoryRouter>,
      );

      const montoSortBtn = screen.getByText('Monto Total Adjudicado');
      fireEvent.click(montoSortBtn);
      expect(onSort).toHaveBeenCalledWith('monto_total_adjudicado');
    });
  });

  describe('ProveedorComparator', () => {
    it('renders comparative modal with multiple suppliers and can close', () => {
      const onClose = vi.fn();
      render(
        <ProveedorComparator
          isOpen={true}
          initialSuppliers={FALLBACK_PROVEEDORES.slice(0, 2)}
          onClose={onClose}
        />,
      );

      expect(screen.getByText(/Comparador Competitivo de Proveedores/i)).toBeInTheDocument();
      expect(screen.getByText('2 / 3')).toBeInTheDocument();

      const closeBtn = screen.getByRole('button', { name: /cerrar comparador/i });
      fireEvent.click(closeBtn);
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('ProveedorDetailPage', () => {
    it('renders supplier detail profile with KPIs, buyers and awards', async () => {
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/proveedores/1']}>
            <Routes>
              <Route path="/proveedores/:id" element={<ProveedorDetailPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByText('Ortopedia y Equipos Médicos Austral SpA'),
      ).toBeInTheDocument();

      // Check RUT
      expect(screen.getByText(/76\.432\.189-5/)).toBeInTheDocument();

      // Check KPIs exist
      expect(screen.getAllByText('Monto Adjudicado').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Contratos Ganados')).toBeInTheDocument();
      expect(screen.getByText('Tasa de Éxito')).toBeInTheDocument();
      expect(screen.getByText('Cuota de Mercado')).toBeInTheDocument();

      // Check buyers section
      expect(screen.getByText('Principales Organismos Compradores')).toBeInTheDocument();

      // Check compare button opens comparator
      const compareBtn = screen.getByRole('button', { name: /comparar con competidores/i });
      fireEvent.click(compareBtn);
      expect(screen.getByText(/Comparador Competitivo de Proveedores/i)).toBeInTheDocument();
    });
  });
});
