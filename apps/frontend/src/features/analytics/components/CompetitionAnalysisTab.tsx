import React from 'react';
import { Target, TrendingDown, Users } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { AdvancedAnalyticsData } from '../hooks/useAdvancedAnalytics';

interface CompetitionAnalysisTabProps {
  data: AdvancedAnalyticsData['competitionAnalysis'];
}

export const CompetitionAnalysisTab: React.FC<CompetitionAnalysisTabProps> = ({ data }) => {
  return (
    <div className="space-y-6">
      {/* 2 KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Oferentes Promedio por Licitación
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-3 font-mono text-2xl font-bold text-primary">
            {data.oferentesPromedio != null ? `${data.oferentesPromedio.toFixed(1)} ofertas` : '—'}
          </p>
          <span className="mt-1 block text-xs text-muted-foreground">
            {data.totalAdjudicacionesConOferentes > 0
              ? `Sobre ${data.totalAdjudicacionesConOferentes} adjudicaciones con oferentes registrados`
              : 'Sin adjudicaciones con conteo de oferentes registrado aún'}
          </span>
        </Card>

        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Margen de Descuento Promedio
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-3 font-mono text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {data.margenDescuentoPromedio != null ? `${data.margenDescuentoPromedio.toFixed(1)}%` : '—'}
          </p>
          <span className="mt-1 block text-xs text-muted-foreground">
            Diferencia promedio entre monto adjudicado y monto estimado
          </span>
        </Card>
      </div>

      {/* Distribution of Bidders */}
      <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
        <CardHeader className="p-0 pb-4">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Target className="h-4 w-4 text-primary" />
            <span>Distribución de Intensidad Competitiva por Licitación</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 p-0">
          {data.distribucionOfertas.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Sin adjudicaciones con conteo de oferentes registrado aún.
            </p>
          )}
          {data.distribucionOfertas.map((item, idx) => (
            <div key={idx} className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="font-semibold text-foreground">{item.rango_oferentes}</span>
                <span className="font-mono text-primary font-semibold">
                  {item.porcentaje_procesos}% de los procesos
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-primary"
                  style={{ width: `${item.porcentaje_procesos}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};
