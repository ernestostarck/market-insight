import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  LicitacionesTable,
  ColumnVisibilitySelector,
  CursorPagination,
  LicitacionAiInsights,
  DEFAULT_COLUMNS,
  FALLBACK_LICITACIONES,
} from '@/features/licitaciones';
import { LicitacionDetailPage } from '@/pages/LicitacionDetailPage';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Licitaciones Feature Module', () => {
  describe('LicitacionesTable', () => {
    it('renders tender rows with code, title, amount in CLP, and status badge', () => {
      render(
        <MemoryRouter>
          <LicitacionesTable items={FALLBACK_LICITACIONES.slice(0, 2)} />
        </MemoryRouter>,
      );

      // Check codes
      expect(screen.getByText('1057416-24-LE26')).toBeInTheDocument();
      expect(screen.getByText('1244-18-LP26')).toBeInTheDocument();

      // Check title
      expect(screen.getByText(/Adquisición de Camas Clínicas Eléctricas/i)).toBeInTheDocument();

      // Check formatted CLP currency
      expect(screen.getByText(/\$128\.500\.000/)).toBeInTheDocument();

      // Check action links
      const viewLinks = screen.getAllByRole('link', { name: /ver ficha/i });
      expect(viewLinks.length).toBeGreaterThanOrEqual(2);
      const hrefs = viewLinks.map((link) => link.getAttribute('href'));
      expect(hrefs).toContain('/licitaciones/101');
      expect(hrefs).toContain('/licitaciones/102');
    });

    it('renders empty state when no tenders match criteria', () => {
      render(
        <MemoryRouter>
          <LicitacionesTable items={[]} />
        </MemoryRouter>,
      );

      expect(screen.getByText(/no se encontraron licitaciones/i)).toBeInTheDocument();
    });
  });

  describe('ColumnVisibilitySelector', () => {
    it('allows toggling column visibility', () => {
      const onToggle = vi.fn();
      const onReset = vi.fn();

      render(
        <ColumnVisibilitySelector
          columns={DEFAULT_COLUMNS}
          onToggleColumn={onToggle}
          onResetColumns={onReset}
        />,
      );

      // Open selector dropdown
      const button = screen.getByTitle(/personalizar columnas/i);
      fireEvent.click(button);

      // Verify column options are shown
      expect(screen.getByText('Monto Estimado')).toBeInTheDocument();
      expect(screen.getByText('Organismo Comprador')).toBeInTheDocument();

      // Click on a toggleable column
      const organismoLabel = screen.getByText('Organismo Comprador');
      fireEvent.click(organismoLabel);
      expect(onToggle).toHaveBeenCalledWith('organismo');
    });
  });

  describe('CursorPagination', () => {
    it('renders current range and handles previous/next page clicks', () => {
      const onNext = vi.fn();
      const onPrevious = vi.fn();

      render(
        <CursorPagination
          total={35}
          pageSize={10}
          pageNumber={2}
          hasNext={true}
          hasPrevious={true}
          onNext={onNext}
          onPrevious={onPrevious}
        />,
      );

      expect(screen.getByText('11 - 20')).toBeInTheDocument();
      expect(screen.getByText('35')).toBeInTheDocument();

      const prevBtn = screen.getByRole('button', { name: /anterior/i });
      const nextBtn = screen.getByRole('button', { name: /siguiente/i });

      expect(prevBtn).not.toBeDisabled();
      expect(nextBtn).not.toBeDisabled();

      fireEvent.click(nextBtn);
      expect(onNext).toHaveBeenCalledTimes(1);

      fireEvent.click(prevBtn);
      expect(onPrevious).toHaveBeenCalledTimes(1);
    });

    it('disables previous button on first page', () => {
      render(
        <CursorPagination
          total={15}
          pageSize={10}
          pageNumber={1}
          hasNext={true}
          hasPrevious={false}
          onNext={vi.fn()}
          onPrevious={vi.fn()}
        />,
      );

      const prevBtn = screen.getByRole('button', { name: /anterior/i });
      expect(prevBtn).toBeDisabled();
    });
  });

  describe('LicitacionAiInsights', () => {
    it('renders AI confidence score, tags and executive summary', () => {
      render(
        <LicitacionAiInsights
          insights={{
            categoria_predicha: 'Camas Clínicas Geriátricas',
            confianza: 0.95,
            es_relevante_geriatria: true,
            es_relevante_discapacidad: true,
            conceptos_clave: ['Trendelenburg', 'IEC 60601-2-52'],
            entidades_extraidas: [{ texto: 'Hospital San Juan de Dios', etiqueta: 'ORGANISMO' }],
            resumen_ejecutivo: 'Proceso de alta relevancia para el sector geriátrico.',
            oportunidad_score: 94,
          }}
        />,
      );

      expect(screen.getByText('95% Confianza')).toBeInTheDocument();
      expect(screen.getByText('Pertinencia Geriatría')).toBeInTheDocument();
      expect(screen.getByText('Pertinencia Discapacidad')).toBeInTheDocument();
      expect(screen.getByText('#Trendelenburg')).toBeInTheDocument();
      expect(screen.getByText('ORGANISMO')).toBeInTheDocument();
      expect(
        screen.getByText('Proceso de alta relevancia para el sector geriátrico.'),
      ).toBeInTheDocument();
    });
  });

  describe('LicitacionDetailPage', () => {
    it('renders detail view with tabs and switching capability', async () => {
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/licitaciones/101']}>
            <Routes>
              <Route path="/licitaciones/:id" element={<LicitacionDetailPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );

      // Verify code in hero
      expect(await screen.findByText('1057416-24-LE26')).toBeInTheDocument();
      const organismElements = screen.getAllByText(/Hospital San Juan de Dios/i);
      expect(organismElements.length).toBeGreaterThanOrEqual(1);

      // Check tab buttons exist
      expect(screen.getByRole('button', { name: /ficha general/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /ítems demandados/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /ofertas presentadas/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cuadro de adjudicación/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /documentos y bases/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /inteligencia artificial/i })).toBeInTheDocument();

      // Switch to items tab
      const itemsTab = screen.getByRole('button', { name: /ítems demandados/i });
      fireEvent.click(itemsTab);

      expect(
        await screen.findByText(/Camas clínicas eléctricas multipropósito/i),
      ).toBeInTheDocument();
    });
  });
});
