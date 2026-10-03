import { MOCK_USER } from './mockAuth';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  AIDocumentsTable,
  AIReviewModal,
  DataQualityCard,
} from '@/features/ai';
import { AIPage } from '@/pages/AIPage';
import { AppRouter } from '@/app/router';
import { AuthContext } from '@/features/auth/context/AuthContext';
import type { AIReviewQueueItem, AIReviewStats, SystemStatus } from '@/types/ai';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

// Fixture matching the real /ai/reviews shape (app/schemas/nlp.py ReviewQueueItemResponse)
const SAMPLE_QUEUE_ITEM: AIReviewQueueItem = {
  classification_id: 'c1111111-1111-1111-1111-111111111111',
  licitacion_id: 101,
  licitacion_codigo: '1057416-24-LE26',
  title: 'Adquisición de Camas Clínicas Eléctricas de 4 Secciones para Unidad de Geriatría',
  organismo: 'Hospital San Juan de Dios',
  monto_estimado: 128500000,
  item_names: ['Cama clínica eléctrica de 4 secciones'],
  confidence_score: 0.964,
  confidence_level: 'HIGH',
  relevance_score: 0.92,
  relevance_tier: 'high',
  category_code: 'medical-equipment',
  subcategory_code: 'geriatric-care',
  winning_method: 'rule',
  rule_score: 0.97,
  similarity_score: 0.9,
  model_score: 0.95,
  explanation: { hybrid: { winning_method: 'rule' } },
  needs_review: false,
  review_reasons: [],
  priority_score: 0.1,
};

const LOW_CONFIDENCE_ITEM: AIReviewQueueItem = {
  ...SAMPLE_QUEUE_ITEM,
  classification_id: 'c2222222-2222-2222-2222-222222222222',
  licitacion_codigo: '2234-15-LE26',
  confidence_score: 0.642,
  confidence_level: 'LOW',
  needs_review: true,
  review_reasons: ['low_confidence'],
};

const SAMPLE_STATS: AIReviewStats = {
  total_reviews: 10,
  accepted_count: 6,
  modified_count: 2,
  acceptance_rate: 0.8,
  unreviewed_classifications: 4,
};

// Fixture matching the real GET /system/status shape (app/schemas/system.py)
const SAMPLE_SYSTEM_STATUS: SystemStatus = {
  status: 'degraded',
  timestamp: '2026-03-15T12:00:00Z',
  app_name: 'MercadoInsight API',
  version: '1.0.0',
  environment: 'production',
  components: {
    api: { status: 'healthy', message: 'FastAPI process running', latency_ms: 0.5 },
    postgres: { status: 'healthy', message: 'PostgreSQL connection pool healthy', latency_ms: 4.2 },
    redis: { status: 'healthy', message: 'Redis cache and broker responding', latency_ms: 1.1 },
    minio: { status: 'degraded', message: 'Object storage slow to respond', latency_ms: 850.0 },
    chilecompra: { status: 'healthy', message: 'MercadoPublico public API responding', latency_ms: 210.4 },
  },
  etl: {
    status: 'healthy',
    last_run_timestamp: '2026-03-15T11:00:00Z',
    data_freshness_seconds: 3600,
  },
  data_quality: {
    score: 97.8,
    status: 'healthy',
    last_evaluated: '2026-03-15T11:05:00Z',
  },
  availability: {
    technical: { status: 'degraded', reasons: ['minio: Object storage slow to respond'] },
    data: { status: 'healthy', reasons: [] },
  },
};

describe('Módulo IA, Human-in-the-Loop & Calidad de Datos (Subfases 7.26, 7.27, 7.28, 7.29)', () => {
  describe('AIDocumentsTable (Subfase 7.26)', () => {
    it('renders real /ai/reviews queue items with stats and confidence badges', async () => {
      render(
        <AIDocumentsTable
          documents={[SAMPLE_QUEUE_ITEM, LOW_CONFIDENCE_ITEM]}
          isLoading={false}
          filters={{}}
          stats={SAMPLE_STATS}
          onFilterChange={vi.fn()}
          onResetFilters={vi.fn()}
          onAccept={vi.fn()}
          onModify={vi.fn()}
        />,
      );

      // Real stats from /ai/reviews/stats, not derived from the fake local array
      expect(screen.getByText('Sin revisar')).toBeInTheDocument();
      expect(screen.getByText('4')).toBeInTheDocument();
      expect(screen.getByText('80.0%')).toBeInTheDocument();

      // Row content sourced from real fields (licitacion_codigo, organismo, category_code)
      expect(screen.getByText('1057416-24-LE26')).toBeInTheDocument();
      expect(screen.getAllByText('medical-equipment')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Hospital San Juan de Dios')[0]).toBeInTheDocument();

      // High confidence row
      expect(screen.getByText('96%')).toBeInTheDocument();

      // Low confidence row, flagged for review with its real reason
      expect(screen.getByText('2234-15-LE26')).toBeInTheDocument();
      expect(screen.getByText('64%')).toBeInTheDocument();
      expect(screen.getByText('low_confidence')).toBeInTheDocument();
    });

    it('filters documents when searching by text query', async () => {
      const onFilterChange = vi.fn();
      render(
        <AIDocumentsTable
          documents={[SAMPLE_QUEUE_ITEM]}
          isLoading={false}
          filters={{}}
          onFilterChange={onFilterChange}
          onResetFilters={vi.fn()}
          onAccept={vi.fn()}
          onModify={vi.fn()}
        />,
      );

      const searchInput = screen.getByPlaceholderText(/buscar por código de licitación/i);
      fireEvent.change(searchInput, { target: { value: 'Grúas' } });

      expect(onFilterChange).toHaveBeenCalledWith({ q: 'Grúas' });
    });
  });

  describe('AIReviewModal (Subfase 7.27 Human-in-the-loop)', () => {
    it('displays real source facts vs AI inference scores', () => {
      render(
        <AIReviewModal
          document={SAMPLE_QUEUE_ITEM}
          isOpen={true}
          onClose={vi.fn()}
          onAccept={vi.fn()}
          onModify={vi.fn()}
        />,
      );

      expect(screen.getByText('Revisión de Clasificación NLP')).toBeInTheDocument();
      expect(screen.getByText('1057416-24-LE26')).toBeInTheDocument();

      // Real source facts (joined from core.licitacion/core.organismo)
      expect(screen.getByText('Datos Fuente (ChileCompra)')).toBeInTheDocument();
      expect(screen.getAllByText('Hospital San Juan de Dios')[0]).toBeInTheDocument();
      expect(screen.getByText(/\$128\.500\.000/)).toBeInTheDocument();

      // Real classifier scores, not fabricated model/embedding version strings
      expect(screen.getByText('Inferencia IA / NLP')).toBeInTheDocument();
      expect(screen.getByText('Confianza: 96%')).toBeInTheDocument();
      expect(screen.getByText('medical-equipment')).toBeInTheDocument();
      expect(screen.getByText('Puntajes del clasificador híbrido')).toBeInTheDocument();
      expect(screen.getByText('97%')).toBeInTheDocument(); // rule_score

      // Real item names from core.licitacion_item, standing in for fabricated "productos_detectados"
      expect(screen.getByText('Cama clínica eléctrica de 4 secciones')).toBeInTheDocument();
    });

    it('allows accepting AI recommendation, persisted via POST /ai/reviews/{id}/accept', () => {
      const onAccept = vi.fn();
      const onClose = vi.fn();

      render(
        <AIReviewModal
          document={LOW_CONFIDENCE_ITEM}
          isOpen={true}
          onClose={onClose}
          onAccept={onAccept}
          onModify={vi.fn()}
        />,
      );

      expect(screen.getByText(/Requiere revisión/i)).toBeInTheDocument();

      const acceptButton = screen.getByText('Aceptar Recomendación IA');
      fireEvent.click(acceptButton);

      expect(onAccept).toHaveBeenCalledWith(
        expect.objectContaining({ classificationId: LOW_CONFIDENCE_ITEM.classification_id }),
      );
      expect(onClose).toHaveBeenCalled();
    });

    it('allows manual correction, persisted via POST /ai/reviews/{id}/modify', () => {
      const onModify = vi.fn();
      const onClose = vi.fn();

      render(
        <AIReviewModal
          document={LOW_CONFIDENCE_ITEM}
          isOpen={true}
          onClose={onClose}
          onAccept={vi.fn()}
          onModify={onModify}
        />,
      );

      fireEvent.click(screen.getByText('Corregir Clasificación'));
      expect(screen.getByText('Reclasificación Manual Human-in-the-Loop')).toBeInTheDocument();

      const inputs = screen.getAllByRole('textbox');
      fireEvent.change(inputs[0], { target: { value: 'assistive-technology' } });
      fireEvent.change(inputs[2], { target: { value: 'Reclasificado tras revisar bases técnicas' } });

      fireEvent.click(screen.getByText('Confirmar Corrección'));

      expect(onModify).toHaveBeenCalledWith(
        expect.objectContaining({
          classificationId: LOW_CONFIDENCE_ITEM.classification_id,
          categoryCode: 'assistive-technology',
        }),
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('DataQualityCard (Subfase 7.28)', () => {
    it('renders real per-component health, ETL freshness and quality score from GET /system/status', () => {
      render(<DataQualityCard status={SAMPLE_SYSTEM_STATUS} />);

      // Real per-component checks (app/monitoring/health.py), not fabricated ETL/NLP labels
      expect(screen.getByText('API Backend')).toBeInTheDocument();
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
      expect(screen.getByText('API ChileCompra')).toBeInTheDocument();
      expect(screen.getByText('850.0')).toBeInTheDocument(); // minio latency_ms

      // Real quality score from DATA_QUALITY_SCORE gauge
      expect(screen.getByText('97.8%')).toBeInTheDocument();
      expect(screen.getByText(/Puntaje de Calidad de Datos/i)).toBeInTheDocument();
      expect(screen.getByText('2026-03-15T11:00:00Z')).toBeInTheDocument(); // etl.last_run_timestamp

      // Real technical vs data availability, each with its own concrete reason
      expect(screen.getAllByText('minio: Object storage slow to respond')[0]).toBeInTheDocument();
    });

    it('shows an honest error state instead of fabricated data when /system/status fails', () => {
      render(<DataQualityCard status={undefined} isError />);

      expect(
        screen.getByText(/No se pudo obtener el estado del sistema/i),
      ).toBeInTheDocument();
      expect(screen.queryByText('97.8%')).not.toBeInTheDocument();
    });
  });

  describe('AIPage & AppRouter (Subfases 7.26 - 7.30)', () => {
    it('renders AIPage with navigation tabs and updates view', async () => {
      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AIPage />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      // Verify title
      expect(
        await screen.findByText('Inteligencia Artificial & Calidad de Datos'),
      ).toBeInTheDocument();

      // Verify tab buttons
      const pendingTab = screen.getByText(/Cola de Revisión Humana/i);
      expect(pendingTab).toBeInTheDocument();

      const qualityTab = screen.getByText(/Salud del Sistema & Calidad ETL/i);
      expect(qualityTab).toBeInTheDocument();

      // Switch to Calidad tab — no API mocked here, so the real, honest error state renders
      fireEvent.click(qualityTab);

      expect(
        await screen.findByText(/No se pudo obtener el estado del sistema/i),
      ).toBeInTheDocument();

      // Switch to Pending tab
      fireEvent.click(pendingTab);
      expect(await screen.findByText(/Cola de Prioridad Human-in-the-Loop/i)).toBeInTheDocument();
    });

    it('loads lazy routed /ai module with ProtectedLayout in AppRouter', async () => {
      const queryClient = createTestQueryClient();
      const mockAuthValue = {
        user: { ...MOCK_USER, email: 'analista@marketinsight.cl', role: 'analyst' as const },
        token: 'mock-valid-jwt-token',
        isAuthenticated: true,
        isLoading: false,
        login: async () => ({ status: 'authenticated' as const }),
        verifyMfa: async () => {},
        logout: async () => {},
        checkAuth: async () => {},
        setUser: () => {},
      };

      render(
        <AuthContext.Provider value={mockAuthValue}>
          <QueryClientProvider client={queryClient}>
            <MemoryRouter initialEntries={['/ai']}>
              <AppRouter />
            </MemoryRouter>
          </QueryClientProvider>
        </AuthContext.Provider>,
      );

      // Router uses React.lazy and Suspense
      expect(
        await screen.findByText('Inteligencia Artificial & Calidad de Datos'),
      ).toBeInTheDocument();
    });
  });
});
