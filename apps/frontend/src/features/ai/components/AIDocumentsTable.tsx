import { useState } from 'react';
import {
  Search,
  Sparkles,
  AlertTriangle,
  FileText,
  RotateCcw,
  Eye,
  ShieldCheck,
} from 'lucide-react';
import type { AIFilters, AIReviewAcceptAction, AIReviewModifyAction, AIReviewQueueItem, AIReviewStats } from '@/types/ai';
import { AIReviewModal } from './AIReviewModal';

interface AIDocumentsTableProps {
  documents: AIReviewQueueItem[];
  isLoading: boolean;
  filters: AIFilters;
  stats?: AIReviewStats;
  onFilterChange: (filters: Partial<AIFilters>) => void;
  onResetFilters: () => void;
  onAccept: (action: AIReviewAcceptAction) => void;
  onModify: (action: AIReviewModifyAction) => void;
}

const CONFIDENCE_BADGE: Record<string, string> = {
  HIGH: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  MEDIUM: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30',
  LOW: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
};

export function AIDocumentsTable({
  documents,
  isLoading,
  filters,
  stats,
  onFilterChange,
  onResetFilters,
  onAccept,
  onModify,
}: AIDocumentsTableProps) {
  const [selectedDoc, setSelectedDoc] = useState<AIReviewQueueItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleOpenReview = (doc: AIReviewQueueItem) => {
    setSelectedDoc(doc);
    setIsModalOpen(true);
  };

  const handleCloseReview = () => {
    setIsModalOpen(false);
    setSelectedDoc(null);
  };

  return (
    <div className="space-y-4">
      {/* KPI Cards — real aggregates from /ai/reviews/stats, not derived from the current page */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground font-medium">Sin revisar</span>
              <FileText className="h-4 w-4 text-primary" />
            </div>
            <p className="text-2xl font-bold text-foreground mt-1">{stats.unreviewed_classifications}</p>
            <span className="text-[11px] text-muted-foreground">Clasificaciones totales</span>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground font-medium">Tasa de Aceptación</span>
              <Sparkles className="h-4 w-4 text-sky-500" />
            </div>
            <p className="text-2xl font-bold text-foreground mt-1">{(stats.acceptance_rate * 100).toFixed(1)}%</p>
            <span className="text-[11px] text-muted-foreground">De {stats.total_reviews} revisiones humanas</span>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground font-medium">En esta cola</span>
              <AlertTriangle className="h-4 w-4 text-amber-500" />
            </div>
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{documents.length}</p>
            <span className="text-[11px] text-muted-foreground">Requieren atención humana</span>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground font-medium">Corregidas</span>
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
            </div>
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{stats.modified_count}</p>
            <span className="text-[11px] text-muted-foreground">Human-in-the-Loop</span>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Buscar por código de licitación, organismo o categoría..."
              value={filters.q || ''}
              onChange={(e) => onFilterChange({ q: e.target.value })}
              className="w-full pl-11 pr-4 py-2 text-xs rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {filters.q && (
            <button
              onClick={onResetFilters}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Limpiar
            </button>
          )}
        </div>
      </div>

      {/* Table Content */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/40 border-b border-border text-muted-foreground uppercase text-[11px] font-semibold">
              <tr>
                <th className="py-3 px-4">Licitación / Organismo</th>
                <th className="py-3 px-4">Categoría NLP</th>
                <th className="py-3 px-4 text-center">Confianza</th>
                <th className="py-3 px-4">Método</th>
                <th className="py-3 px-4">Motivo de revisión</th>
                <th className="py-3 px-4 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y border-border divide-border/60">
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="py-4 px-4 space-y-2">
                      <div className="h-3 bg-muted rounded w-28" />
                      <div className="h-2.5 bg-muted rounded w-48" />
                    </td>
                    <td className="py-4 px-4 space-y-1">
                      <div className="h-3 bg-muted rounded w-36" />
                    </td>
                    <td className="py-4 px-4 text-center"><div className="h-4 bg-muted rounded w-12 mx-auto" /></td>
                    <td className="py-4 px-4"><div className="h-3 bg-muted rounded w-20" /></td>
                    <td className="py-4 px-4"><div className="h-3 bg-muted rounded w-24" /></td>
                    <td className="py-4 px-4 text-right"><div className="h-6 bg-muted rounded w-16 ml-auto" /></td>
                  </tr>
                ))
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted-foreground">
                    No hay clasificaciones que requieran revisión con los filtros seleccionados.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => {
                  const confidencePercent = Math.round(doc.confidence_score * 100);

                  return (
                    <tr key={doc.classification_id} className="hover:bg-muted/30 transition-colors group">
                      <td className="py-3.5 px-4">
                        <div className="font-mono font-bold text-foreground text-xs">
                          {doc.licitacion_codigo ?? `#${doc.licitacion_id}`}
                        </div>
                        <div className="text-muted-foreground line-clamp-1 max-w-xs text-[11px]" title={doc.title ?? ''}>
                          {doc.title ?? 'Sin título'}
                        </div>
                        {doc.organismo && (
                          <div className="text-[10px] text-primary font-medium mt-0.5">{doc.organismo}</div>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-foreground">{doc.category_code ?? 'Sin categoría'}</div>
                        {doc.subcategory_code && (
                          <div className="text-muted-foreground text-[11px]">{doc.subcategory_code}</div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border ${CONFIDENCE_BADGE[doc.confidence_level] ?? CONFIDENCE_BADGE.LOW}`}
                        >
                          {doc.confidence_level === 'LOW' && <AlertTriangle className="h-3 w-3 shrink-0" />}
                          {confidencePercent}%
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-muted text-foreground">
                          {doc.winning_method ?? '—'}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1">
                          {doc.review_reasons.map((reason) => (
                            <span key={reason} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300">
                              {reason}
                            </span>
                          ))}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handleOpenReview(doc)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border border-border bg-background hover:bg-muted text-foreground transition-colors shadow-xs"
                        >
                          <Eye className="h-3.5 w-3.5 text-primary" />
                          Auditar
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AIReviewModal
        document={selectedDoc}
        isOpen={isModalOpen}
        onClose={handleCloseReview}
        onAccept={onAccept}
        onModify={onModify}
      />
    </div>
  );
}
