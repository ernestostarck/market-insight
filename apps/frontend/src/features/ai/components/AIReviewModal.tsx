import { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Cpu,
  Layers,
  Edit3,
} from 'lucide-react';
import type { AIReviewAcceptAction, AIReviewModifyAction, AIReviewQueueItem } from '@/types/ai';
import { formatCLP } from '@/lib/formatters';

interface AIReviewModalProps {
  document: AIReviewQueueItem | null;
  isOpen: boolean;
  onClose: () => void;
  onAccept: (action: AIReviewAcceptAction) => void;
  onModify: (action: AIReviewModifyAction) => void;
}

export function AIReviewModal({ document, isOpen, onClose, onAccept, onModify }: AIReviewModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [correctedCategoria, setCorrectedCategoria] = useState('');
  const [correctedSubcategoria, setCorrectedSubcategoria] = useState('');
  const [notes, setNotes] = useState('');

  if (!isOpen || !document) return null;

  const confidencePercent = Math.round(document.confidence_score * 100);

  const handleAccept = () => {
    onAccept({
      classificationId: document.classification_id,
      reason: notes || undefined,
    });
    onClose();
  };

  const handleCorrect = () => {
    if (!correctedCategoria.trim()) return;
    onModify({
      classificationId: document.classification_id,
      categoryCode: correctedCategoria.trim(),
      subcategoryCode: correctedSubcategoria.trim() || undefined,
      reason: notes || 'Corrección manual de categoría según revisión del analista.',
    });
    setIsEditing(false);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in-0"
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-card border border-border rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="review-modal-title" className="text-lg font-bold text-foreground">
                  Revisión de Clasificación NLP
                </h2>
                {document.licitacion_codigo && (
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    {document.licitacion_codigo}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{document.title}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="Cerrar modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body with scroll */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {document.needs_review && (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-bold">Requiere revisión ({document.review_reasons.join(', ') || 'sin motivo específico'}):</span>{' '}
                Esta clasificación fue marcada por el pipeline híbrido para validación humana antes de usarse en las métricas del observatorio.
              </div>
            </div>
          )}

          {/* Source facts vs AI inference */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg border border-border/80 bg-muted/20 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-border/60">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Datos Fuente (ChileCompra)
                </h3>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                  Hecho Verificado
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Organismo Comprador:</span>
                  <span className="font-semibold text-foreground">{document.organismo ?? 'No disponible'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Presupuesto Estimado:</span>
                  <span className="font-semibold text-foreground font-mono">
                    {document.monto_estimado != null ? formatCLP(document.monto_estimado) : 'No disponible'}
                  </span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg border border-primary/30 bg-primary/5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-primary/20">
                <h3 className="text-xs font-bold uppercase tracking-wider text-primary">Inferencia IA / NLP</h3>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border bg-muted text-muted-foreground">
                  Confianza: {confidencePercent}%
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Categoría Sugerida:</span>
                  <span className="font-semibold text-foreground">{document.category_code ?? 'Sin categoría'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Subcategoría:</span>
                  <span className="font-semibold text-foreground">{document.subcategory_code ?? '—'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Método ganador:</span>
                  <span className="text-primary font-medium">{document.winning_method ?? '—'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Nivel de relevancia:</span>
                  <span className="text-foreground font-medium">{document.relevance_tier ?? '—'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Real component scores of the hybrid classifier */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-primary" />
              Puntajes del clasificador híbrido
            </h3>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2 rounded-md bg-muted/60 text-center">
                <div className="text-muted-foreground text-[10px]">Reglas</div>
                <div className="font-mono font-bold text-foreground">
                  {document.rule_score != null ? `${Math.round(document.rule_score * 100)}%` : '—'}
                </div>
              </div>
              <div className="p-2 rounded-md bg-muted/60 text-center">
                <div className="text-muted-foreground text-[10px]">Similitud semántica</div>
                <div className="font-mono font-bold text-foreground">
                  {document.similarity_score != null ? `${Math.round(document.similarity_score * 100)}%` : '—'}
                </div>
              </div>
              <div className="p-2 rounded-md bg-muted/60 text-center">
                <div className="text-muted-foreground text-[10px]">Modelo supervisado</div>
                <div className="font-mono font-bold text-foreground">
                  {document.model_score != null ? `${Math.round(document.model_score * 100)}%` : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Real product/item names from core.licitacion_item */}
          {document.item_names.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-primary" />
                Ítems de la licitación
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {document.item_names.map((name, idx) => (
                  <span key={idx} className="text-[11px] px-2 py-1 rounded-md bg-muted text-foreground">
                    {name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Real explanation payload from the classifier */}
          {document.explanation && Object.keys(document.explanation).length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Explicación del clasificador</h3>
              <pre className="text-[11px] p-3 rounded-lg bg-muted/40 border border-border/60 overflow-x-auto text-foreground">
                {JSON.stringify(document.explanation, null, 2)}
              </pre>
            </div>
          )}

          {/* Manual correction form */}
          {isEditing && (
            <div className="p-4 rounded-lg border border-primary/40 bg-primary/5 text-xs space-y-3 animate-in fade-in-50">
              <h4 className="font-bold text-foreground">Reclasificación Manual Human-in-the-Loop</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-muted-foreground mb-1">Nuevo código de categoría</label>
                  <input
                    type="text"
                    value={correctedCategoria}
                    onChange={(e) => setCorrectedCategoria(e.target.value)}
                    placeholder="Ej. medical-equipment"
                    className="w-full px-3 py-1.5 rounded-md border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-muted-foreground mb-1">Nuevo código de subcategoría</label>
                  <input
                    type="text"
                    value={correctedSubcategoria}
                    onChange={(e) => setCorrectedSubcategoria(e.target.value)}
                    placeholder="Ej. movilidad_reducida"
                    className="w-full px-3 py-1.5 rounded-md border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[11px] text-muted-foreground mb-1">Motivo de corrección (obligatorio)</label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Ej. Las bases exigen especificación para uso neurológico"
                  className="w-full px-3 py-1.5 rounded-md border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1.5 rounded-md text-xs border border-border text-muted-foreground hover:text-foreground"
                >
                  Cancelar Corrección
                </button>
                <button
                  type="button"
                  onClick={handleCorrect}
                  disabled={!correctedCategoria.trim() || notes.trim().length < 3}
                  className="px-3 py-1.5 rounded-md text-xs bg-primary text-primary-foreground font-semibold hover:bg-primary/90 disabled:opacity-50"
                >
                  Confirmar Corrección
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-muted/20">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            Cerrar
          </button>

          {!isEditing && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setCorrectedCategoria(document.category_code ?? '');
                  setCorrectedSubcategoria(document.subcategory_code ?? '');
                  setIsEditing(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 transition-colors"
              >
                <Edit3 className="h-3.5 w-3.5" />
                Corregir Clasificación
              </button>
              <button
                type="button"
                onClick={handleAccept}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Aceptar Recomendación IA
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
