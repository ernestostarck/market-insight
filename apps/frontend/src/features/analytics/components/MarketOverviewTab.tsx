import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { TrendingUp, DollarSign, Calendar } from 'lucide-react';
import { formatCLP, formatCompactCurrency } from '@/lib/formatters';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { AdvancedAnalyticsData } from '../hooks/useAdvancedAnalytics';

interface MarketOverviewTabProps {
  data: AdvancedAnalyticsData['marketOverview'];
}

export const MarketOverviewTab: React.FC<MarketOverviewTabProps> = ({ data }) => {
  return (
    <div className="space-y-6">
      {/* Time Series Area Chart */}
      <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
        <CardHeader className="p-0 pb-4">
          <CardTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
            <TrendingUp className="h-4 w-4 text-primary" />
            <span>Serie Temporal de Gasto y Adjudicaciones en Mercado Público</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.serieTemporal} margin={{ top: 10, right: 20, left: 15, bottom: 20 }}>
                <defs>
                  <linearGradient id="colorMontoMarket" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d6efd" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0d6efd" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="mes" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => formatCompactCurrency(v)}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="rounded-lg border border-border/80 bg-popover p-3 text-xs shadow-xl text-popover-foreground">
                          <p className="font-bold">{d.mes}</p>
                          <p className="mt-1 font-mono text-primary font-semibold">
                            Gasto Adjudicado: {formatCLP(d.monto)}
                          </p>
                          <p className="mt-0.5 text-muted-foreground">
                            {d.licitaciones} licitaciones • {d.adjudicaciones} adjudicaciones
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="monto"
                  name="Gasto Adjudicado"
                  stroke="#0d6efd"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorMontoMarket)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Seasonality breakdown */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Calendar className="h-4 w-4 text-primary" />
              <span>Estacionalidad Presupuestaria por Trimestre</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.estacionalidad} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="trimestre" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => formatCompactCurrency(v)}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="rounded-lg border border-border/80 bg-popover p-2.5 text-xs shadow-xl text-popover-foreground">
                            <p className="font-bold">{d.trimestre}</p>
                            <p className="mt-1 font-mono text-primary font-semibold">
                              {formatCLP(d.monto)} ({d.porcentaje}%)
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="monto" fill="#0d6efd" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Real indicators, computed from the same fetched series (no narrative claims) */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Indicadores del Mercado</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-1 text-xs text-foreground">
            {data.estacionalidad.length > 0 ? (
              <div className="rounded-lg border border-border/80 bg-muted/40 p-3">
                <p className="font-semibold text-foreground">Trimestre de mayor gasto adjudicado</p>
                <p className="mt-1 text-muted-foreground">
                  {(() => {
                    const top = [...data.estacionalidad].sort((a, b) => b.porcentaje - a.porcentaje)[0];
                    return `${top.trimestre} concentra el ${top.porcentaje}% del monto adjudicado del período mostrado.`;
                  })()}
                </p>
              </div>
            ) : (
              <div className="rounded-lg border border-border/80 bg-muted/40 p-3 text-muted-foreground">
                Sin adjudicaciones registradas aún para calcular estacionalidad.
              </div>
            )}
            <div className="rounded-lg border border-border/80 bg-muted/40 p-3">
              <p className="font-semibold text-foreground">Tasa de Adjudicación</p>
              <p className="mt-1 text-muted-foreground">
                {data.tasaAdjudicacionEfectiva != null
                  ? `${data.tasaAdjudicacionEfectiva.toFixed(1)}% de las licitaciones publicadas en el período tienen al menos una adjudicación registrada.`
                  : 'Sin licitaciones en el período seleccionado.'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
