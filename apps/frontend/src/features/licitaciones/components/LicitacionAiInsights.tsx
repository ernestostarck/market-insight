import React from 'react';
import { Sparkles, CheckCircle2, AlertCircle, Tag, Layers, Lightbulb } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { LicitacionClasificacionIA } from '@/types';

interface LicitacionAiInsightsProps {
  insights?: LicitacionClasificacionIA | null;
}

export const LicitacionAiInsights: React.FC<LicitacionAiInsightsProps> = ({ insights }) => {
  if (!insights) {
    return (
      <Card className="rounded-xl border border-border/80 bg-card p-6 text-center text-muted-foreground shadow-sm">
        <Sparkles className="mx-auto mb-2 h-8 w-8 text-muted-foreground/60" />
        <p className="text-sm">Análisis de Inteligencia Artificial en proceso de sincronización.</p>
      </Card>
    );
  }

  const confidencePercent = Math.round((insights.confianza || 0.9) * 100);

  return (
    <div className="space-y-6">
      {/* Top Banner with AI Confidence & Relevance Badges */}
      <div className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-foreground">Clasificación de Pertinencia NLP / IA</h3>
                <Badge
                  variant="outline"
                  className="border-emerald-500/20 bg-emerald-50 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                >
                  {confidencePercent}% Confianza
                </Badge>
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {insights.categoria_predicha || 'Equipamiento Asistencial Geriátrico'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {insights.es_relevante_geriatria && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Pertinencia Geriatría
              </span>
            )}
            {insights.es_relevante_discapacidad && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-500/20 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Pertinencia Discapacidad
              </span>
            )}
            {insights.oportunidad_score && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/20 bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
                Score Oportunidad: {insights.oportunidad_score}/100
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      {insights.resumen_ejecutivo && (
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <span>Resumen Ejecutivo Generado por IA</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 pt-2">
            <p className="text-sm leading-relaxed text-foreground">{insights.resumen_ejecutivo}</p>
          </CardContent>
        </Card>
      )}

      {/* Two columns: Detected Concepts & Extracted Entities */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Conceptos Detectados */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Tag className="h-4 w-4 text-primary" />
              <span>Conceptos Clave Detectados</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {insights.conceptos_clave && insights.conceptos_clave.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {insights.conceptos_clave.map((concepto, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center rounded-md border border-border/80 bg-muted/60 px-2.5 py-1 text-xs font-medium text-foreground"
                  >
                    #{concepto}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No se detectaron conceptos adicionales.</p>
            )}
          </CardContent>
        </Card>

        {/* Entidades Extraídas (NER) */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Layers className="h-4 w-4 text-primary" />
              <span>Entidades Técnicas Extraídas (NER)</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {insights.entidades_extraidas && insights.entidades_extraidas.length > 0 ? (
              <div className="space-y-2">
                {insights.entidades_extraidas.map((ent, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-border/80 bg-muted/30 px-3 py-2 text-xs"
                  >
                    <span className="font-medium text-foreground">{ent.texto}</span>
                    <span className="rounded bg-primary/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-primary">
                      {ent.etiqueta}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No se extrajeron entidades estructuradas.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Strategic Recommendations */}
      {insights.recomendaciones && insights.recomendaciones.length > 0 && (
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <AlertCircle className="h-4 w-4 text-primary" />
              <span>Recomendaciones Estratégicas para la Postulación</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 pt-2">
            <ul className="space-y-2">
              {insights.recomendaciones.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-foreground">
                  <div className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
