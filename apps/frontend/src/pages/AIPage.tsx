import { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  Activity,
  FileCheck2,
  RefreshCw,
  MessageSquare,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useAIDocuments,
  useAIReviewStats,
  useDataQuality,
  AIDocumentsTable,
  DataQualityCard,
  ChatView,
} from '@/features/ai';

type AITab = 'expedientes' | 'chat' | 'pendientes' | 'calidad';

export function AIPage() {
  const [activeTab, setActiveTab] = useState<AITab>('expedientes');
  const {
    documents,
    isLoading: isDocsLoading,
    filters,
    setFilters,
    resetFilters,
    acceptReview,
    modifyReview,
    refetch: refetchDocs,
  } = useAIDocuments(activeTab === 'pendientes');

  const { data: reviewStats, refetch: refetchStats } = useAIReviewStats();

  const {
    data: dataQuality,
    isLoading: isQualityLoading,
    isError: isQualityError,
    refetch: refetchQuality,
  } = useDataQuality();

  const handleRefresh = () => {
    refetchDocs();
    refetchStats();
    refetchQuality();
  };

  const pendingReviewCount = reviewStats?.unreviewed_classifications ?? 0;

  return (
    <div className="space-y-6 pb-12">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Inteligencia Artificial & Calidad de Datos
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/20 bg-purple-50 px-2.5 py-0.5 text-xs font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-500 animate-pulse" />
                NLP v1.8.2
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Supervisión del pipeline de clasificación semántica, verificación Human-in-the-Loop y telemetría de ingesta MercadoPúblico.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className="flex items-center gap-2 border-primary/30 text-primary hover:bg-primary hover:text-white font-medium text-xs rounded-md shadow-sm transition-all"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Actualizar Modelos</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-border space-x-1">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'chat'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          Asistente Conversacional RAG
        </button>

        <button
          onClick={() => setActiveTab('expedientes')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'expedientes'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Sparkles className="h-4 w-4" />
          Expedientes & Clasificaciones NLP
        </button>

        <button
          onClick={() => setActiveTab('pendientes')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'pendientes'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Cola de Revisión Humana
          {pendingReviewCount > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-600 dark:text-amber-400">
              {pendingReviewCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('calidad')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'calidad'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Activity className="h-4 w-4" />
          Salud del Sistema & Calidad ETL
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'chat' && (
        <div className="space-y-4">
          <ChatView />
        </div>
      )}

      {activeTab === 'expedientes' && (
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Clasificaciones que en algún momento requirieron atención humana (baja confianza, señales en
            conflicto o categoría sin asignar), revisadas o no.
          </p>
          <AIDocumentsTable
            documents={documents}
            isLoading={isDocsLoading}
            filters={filters}
            stats={reviewStats}
            onFilterChange={setFilters}
            onResetFilters={resetFilters}
            onAccept={acceptReview}
            onModify={modifyReview}
          />
        </div>
      )}

      {activeTab === 'pendientes' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-3">
            <FileCheck2 className="h-5 w-5 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
            <div>
              <h3 className="font-bold text-sm text-foreground">
                Cola de Prioridad Human-in-the-Loop
              </h3>
              <p className="mt-0.5 text-muted-foreground leading-relaxed">
                Clasificaciones aún sin revisar, priorizadas por el motor de confianza del clasificador híbrido.
                Aceptar o corregir queda registrado de forma permanente en la base de datos.
              </p>
            </div>
          </div>

          <AIDocumentsTable
            documents={documents}
            isLoading={isDocsLoading}
            filters={filters}
            stats={reviewStats}
            onFilterChange={setFilters}
            onResetFilters={resetFilters}
            onAccept={acceptReview}
            onModify={modifyReview}
          />
        </div>
      )}

      {activeTab === 'calidad' && (
        <div className="space-y-4">
          <DataQualityCard
            status={dataQuality}
            isLoading={isQualityLoading}
            isError={isQualityError}
            onRefresh={refetchQuality}
          />
        </div>
      )}
    </div>
  );
}
export default AIPage;
