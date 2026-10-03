import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  AdjudicacionesTable,
  FALLBACK_ADJUDICACIONES,
  OrdenesCompraTable,
  FALLBACK_ORDENES_COMPRA,
} from '@/features/adjudicaciones';
import { MarketObjectivePage } from '@/pages/MarketObjectivePage';
import { AdjudicacionesPage } from '@/pages/AdjudicacionesPage';
import { OrdenesCompraPage } from '@/pages/OrdenesCompraPage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Market Objective, Adjudicaciones, Órdenes de Compra & Analytics', () => {
  describe('MarketObjectivePage (Subfase 7.22)', () => {
    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('renders real KPIs and leaders from GET /analytics/market-objective', async () => {
      // Real shape from AnalyticsRepository.market_objective_summary (niche-filtered
      // by the real geriatría/discapacidad domain dictionary, not a fake catalog).
      vi.spyOn(api, 'get').mockResolvedValue({
        kpis: {
          licitaciones_relacionadas: 142,
          monto_total: 4850000000,
          proveedores_activos: 46,
          organismos_activos: 38,
          precio_promedio: 1420000,
        },
        tasa_crecimiento: 18.5,
        tendencias: [{ mes: '2026-03-01', monto: 410000000, licitaciones: 14 }],
        organismos_lideres: [
          { nombre: 'Central de Abastecimiento del SNSS (CENABAST)', rut: null, monto_total: 1850000000, porcentaje: 38.1, contratos: 24 },
        ],
        proveedores_lideres: [
          { nombre: 'Ortopedia y Equipos Médicos Austral SpA', rut: '76.432.189-5', monto_total: 1420500000, porcentaje: 29.3, contratos: 18 },
        ],
        categorias_relacionadas: [
          { codigo: '42192200', nombre: 'Sillas de Ruedas', monto: 1370000000, porcentaje: 28.2 },
        ],
        dictionary_terms_used: 84,
      });

      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <MarketObjectivePage />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByText('Mercado Objetivo: Discapacidad & Geriatría'),
      ).toBeInTheDocument();

      // Real KPIs
      expect(await screen.findByText('142')).toBeInTheDocument();
      expect(screen.getByText(/\$4\.850\.000\.000/)).toBeInTheDocument();
      expect(screen.getByText('+18.5%')).toBeInTheDocument();

      // Real domain-dictionary methodology note, not a fabricated product catalog
      expect(screen.getByText(/84 términos reales/)).toBeInTheDocument();

      // Real leading buyers & suppliers
      expect(
        screen.getByText('Central de Abastecimiento del SNSS (CENABAST)'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Ortopedia y Equipos Médicos Austral SpA'),
      ).toBeInTheDocument();
    });
  });

  describe('Adjudicaciones (Subfase 7.23)', () => {
    it('renders AdjudicacionesTable with CLP amount, RUT and deviation margin', () => {
      render(
        <MemoryRouter>
          <AdjudicacionesTable items={FALLBACK_ADJUDICACIONES.slice(0, 2)} />
        </MemoryRouter>,
      );

      expect(screen.getByText('1057416-24-LE26')).toBeInTheDocument();
      expect(screen.getByText('76.432.189-5')).toBeInTheDocument();
      expect(screen.getByText(/\$128\.500\.000/)).toBeInTheDocument();
      expect(screen.getByText('-6.5%')).toBeInTheDocument();
    });

    it('filters adjudications in AdjudicacionesPage', async () => {
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AdjudicacionesPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(screen.getByText('Historial de Adjudicaciones')).toBeInTheDocument();
      expect(
        await screen.findByText('1057416-24-LE26'),
      ).toBeInTheDocument();

      const searchInput = screen.getByPlaceholderText(/Buscar por código de licitación/i);
      fireEvent.change(searchInput, { target: { value: 'Grúas Eléctricas' } });

      await waitFor(() => {
        expect(
          screen.getByText(/Grúas Eléctricas de Transferencia/i),
        ).toBeInTheDocument();
      });
    });
  });

  describe('Órdenes de Compra (Subfase 7.23)', () => {
    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('renders OrdenesCompraTable with code, status and amount', () => {
      render(
        <MemoryRouter>
          <OrdenesCompraTable items={FALLBACK_ORDENES_COMPRA.slice(0, 2)} />
        </MemoryRouter>,
      );

      expect(screen.getByText('1057416-24-OC1')).toBeInTheDocument();
      expect(screen.getByText('1057416-24-LE26')).toBeInTheDocument();
      expect(screen.getByText('Aceptada')).toBeInTheDocument();
      expect(screen.getByText(/\$64\.250\.000/)).toBeInTheDocument();
    });

    it('filters orders by status in OrdenesCompraPage', async () => {
      vi.spyOn(api, 'get').mockResolvedValue(FALLBACK_ORDENES_COMPRA);
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <OrdenesCompraPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(screen.getByText('Órdenes de Compra')).toBeInTheDocument();
      expect(await screen.findByText('1057416-24-OC1')).toBeInTheDocument();

      // Filter by status 'Recepcionada'
      const statusSelect = screen.getByRole('combobox');
      fireEvent.change(statusSelect, { target: { value: 'Recepcionada' } });

      await waitFor(() => {
        expect(screen.getByText('1057416-24-OC2')).toBeInTheDocument();
        expect(screen.queryByText('1057416-24-OC1')).not.toBeInTheDocument();
      });
    });
  });

  describe('Analytics & Price Analysis (Subfases 7.24 & 7.25)', () => {
    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('renders AnalyticsPage from real /analytics/* endpoints and allows switching tabs to Price Analysis', async () => {
      // Real market/monthly, suppliers/performance, categories/spending and
      // competition/summary shapes — these replaced the removed /analytics/advanced
      // fake blob (see useAdvancedAnalytics.ts).
      vi.spyOn(api, 'get').mockImplementation(async (url: string) => {
        if (url === '/analytics/market/monthly') {
          return [
            { mes: '2026-01-01', total_licitaciones: 10, total_adjudicaciones: 5, monto_total_adjudicado: '1000000.00' },
          ];
        }
        if (url === '/analytics/suppliers/performance') {
          return [
            {
              razon_social: 'Proveedor A', rut: '76.111.111-1', total_adjudicaciones: 3,
              monto_total_adjudicado: '700000.00', ratio_adjudicacion_promedio: '0.9',
              ultima_adjudicacion: '2026-01-15',
            },
            {
              razon_social: 'Proveedor B', rut: '76.222.222-2', total_adjudicaciones: 2,
              monto_total_adjudicado: '300000.00', ratio_adjudicacion_promedio: '0.8',
              ultima_adjudicacion: '2026-01-10',
            },
          ];
        }
        if (url === '/analytics/categories/spending') {
          return [
            {
              categoria: 'Equipamiento Medico', codigo_categoria: '42192000',
              gasto_total_oc: '1000000.00', numero_ordenes_compra: 5, gasto_promedio_oc: '200000.00',
            },
          ];
        }
        if (url === '/analytics/competition/summary') {
          return {
            oferentes_promedio: 3.5, margen_descuento_promedio: 12.5,
            total_adjudicaciones_con_oferentes: 5,
            distribucion_oferentes: [{ rango_oferentes: '2-3 oferentes', total_procesos: 5, porcentaje: 100 }],
          };
        }
        if (url === '/analytics/prices/items') {
          return [
            {
              licitacion_codigo: '1057416-24-LE26', organismo: 'Hospital San Juan de Dios',
              nombre: 'Cama clinica electrica 4 secciones', descripcion: null,
              precio_unitario: '1420000.00', cantidad: '20', unidad: 'Unidad',
              fecha: '2026-01-15', categoria_codigo: '42192200', categoria_nombre: 'Camas Médicas',
            },
          ];
        }
        throw new Error(`unexpected url ${url}`);
      });

      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AnalyticsPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByText('Analytics Avanzado & Inteligencia de Precios'),
      ).toBeInTheDocument();

      // Tab 1: Market Overview
      expect(
        await screen.findByText('Serie Temporal de Gasto y Adjudicaciones en Mercado Público'),
      ).toBeInTheDocument();

      // Switch to Suppliers tab — real HHI computed from the mocked shares (70%^2 + 30%^2 = 5800)
      const suppliersBtn = screen.getByRole('button', { name: /Proveedores & Concentración/i });
      fireEvent.click(suppliersBtn);
      expect(screen.getByText('Índice de Concentración (HHI)')).toBeInTheDocument();
      expect(screen.getByText('5800')).toBeInTheDocument();
      expect(screen.getByText('Proveedor A')).toBeInTheDocument();

      // Switch to Price Analysis tab — real search over core.licitacion_item, no fake catalog
      const pricesBtn = screen.getByRole('button', { name: /Análisis de Precios Homogéneos/i });
      fireEvent.click(pricesBtn);

      expect(
        screen.getByText(/Escribe el nombre de un producto/i),
      ).toBeInTheDocument();

      const searchInput = screen.getByPlaceholderText(/Escribe al menos 2 caracteres/i);
      fireEvent.change(searchInput, { target: { value: 'cama clinica' } });

      expect(await screen.findByText('Precio Mínimo Adjudicado')).toBeInTheDocument();
      expect(screen.getByText('Precio Mediano (P50)')).toBeInTheDocument();
      expect(screen.getByText('Precio Promedio')).toBeInTheDocument();
      expect(screen.getByText('Precio Máximo Adjudicado')).toBeInTheDocument();
      expect(screen.getAllByText('$1.420.000').length).toBeGreaterThan(0);
      expect(screen.getByText('Cama clinica electrica 4 secciones')).toBeInTheDocument();
      expect(screen.getByText(/no hay marca, modelo ni capacidad registrados/i)).toBeInTheDocument();
    });
  });
});
