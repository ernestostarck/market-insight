import React from 'react';
import { Activity, Building2, FileText, RefreshCw, TrendingUp, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { MetricKpiCard } from '@/components/charts/MetricKpiCard';
import { TimeSeriesChart, type TimeSeriesDataPoint } from '@/components/charts/TimeSeriesChart';
import { BarRankingChart, type RankingItem } from '@/components/charts/BarRankingChart';
import {
  DonutDistributionChart,
  type DistributionItem,
} from '@/components/charts/DonutDistributionChart';
import { GlobalFilterBar } from '@/components/filters/GlobalFilterBar';
import { RecentTendersTable } from '@/features/dashboard/components/RecentTendersTable';
import { RecentAwardsTable } from '@/features/dashboard/components/RecentAwardsTable';
import { useDashboardData } from '@/features/dashboard/hooks/useDashboardData';
import { useSegmento } from '@/features/segmento';
import { formatCompactCurrency, formatRelativeTime } from '@/lib/formatters';

export function DashboardPage() {
  const {
    kpis,
    monthlyData,
    suppliersData,
    categoriesData,
    recentTenders,
    recentAwards,
    isFetching,
    dataUpdatedAt,
    refetchAll,
  } = useDashboardData();
  const segmento = useSegmento();

  // Transform monthly data for TimeSeriesChart
  const timeSeriesData: TimeSeriesDataPoint[] = monthlyData.map((m) => {
    const parts = m.mes.split('-');
    const label = `${parts[1]}/${parts[0]?.substring(2)}`;
    return {
      mes: label,
      monto: Number(m.monto_total_adjudicado),
      licitaciones: m.total_licitaciones,
    };
  });

  // Transform suppliers data for BarRankingChart
  const suppliersRanking: RankingItem[] = suppliersData.slice(0, 5).map((s) => ({
    name: s.razon_social.length > 22 ? `${s.razon_social.substring(0, 22)}...` : s.razon_social,
    value: Number(s.monto_total_adjudicado),
    label: `${s.total_adjudicaciones} contratos ganados`,
  }));

  // Transform categories data for BarRankingChart
  const categoriesRanking: RankingItem[] = categoriesData.slice(0, 5).map((c) => ({
    name: c.categoria.length > 22 ? `${c.categoria.substring(0, 22)}...` : c.categoria,
    value: Number(c.gasto_total_oc),
    label: `${c.numero_ordenes_compra} órdenes de compra`,
  }));

  // Distribution of tender states
  const distributionData: DistributionItem[] = [
    { name: 'Publicadas', value: 58, color: '#38bdf8' },
    { name: 'Adjudicadas', value: 46, color: '#10b981' },
    { name: 'Cerradas', value: 24, color: '#94a3b8' },
    { name: 'Desiertas', value: 14, color: '#f59e0b' },
  ];

  return (
    <div className="space-y-6">
      {/* Dashboard Top Control Header */}
      <div className="flex flex-col gap-3 rounded-xl border border-border/80 bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Monitor Ejecutivo de Compras Públicas
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {segmento
              ? `Rubro seleccionado: ${segmento.parentLabel ? `${segmento.parentLabel} › ` : ''}${segmento.label}.`
              : 'Mercado objetivo: Equipos geriátricos, accesibilidad y soluciones para personas con discapacidad.'}
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          {dataUpdatedAt > 0 && (
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Activity className="h-3 w-3 text-emerald-500" />
              Actualizado {formatRelativeTime(new Date(dataUpdatedAt))}
            </span>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchAll()}
            disabled={isFetching}
            className="h-8 gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar datos
          </Button>
        </div>
      </div>

      {/* Global Filter Bar */}
      <GlobalFilterBar />

      {/* 4 Core Executive KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricKpiCard
          title="Licitaciones Activas"
          value={kpis.licitaciones_activas}
          change={8.4}
          changeLabel="vs mes anterior"
          icon={FileText}
          helper="Oportunidades abiertas y en evaluación continua."
        />

        <MetricKpiCard
          title="Monto Adjudicado"
          value={formatCompactCurrency(kpis.monto_total_adjudicado_mes)}
          change={kpis.tasa_crecimiento_monto}
          changeLabel="crecimiento mensual"
          icon={TrendingUp}
          helper="Volumen transaccionado en el período activo."
        />

        <MetricKpiCard
          title="Proveedores Participantes"
          value={kpis.proveedores_activos}
          change={4.2}
          changeLabel="nuevos oferentes"
          icon={Users}
          helper="Oferentes evaluados con ranking histórico."
        />

        <MetricKpiCard
          title="Organismos Compradores"
          value={kpis.organismos_compradores}
          change={-2.1}
          changeLabel="variación"
          icon={Building2}
          helper="Hospitales, municipios y servicios públicos."
        />
      </div>

      {/* Charts Section: Temporal Evolution + Status Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Evolution Over Time Area Chart (2 cols) */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold">
                  Evolución de Compras y Montos Adjudicados
                </CardTitle>
                <CardDescription className="text-xs">
                  Comparativa de volumen de licitaciones (eje der.) vs monto CLP adjudicado (eje
                  izq.)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <TimeSeriesChart data={timeSeriesData} height={300} />
          </CardContent>
        </Card>

        {/* State Distribution Donut Chart (1 col) */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold">Distribución por Estado</CardTitle>
            <CardDescription className="text-xs">
              Estado actual de las convocatorias del sector
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DonutDistributionChart data={distributionData} height={300} />
          </CardContent>
        </Card>
      </div>

      {/* Rankings Section: Top Categories & Top Suppliers */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top Demand Categories */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold">Top 5 Rubros con Mayor Demanda</CardTitle>
            <CardDescription className="text-xs">
              Gasto total acumulado en órdenes de compra por categoría técnica
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BarRankingChart data={categoriesRanking} height={260} valueIsCurrency={true} />
          </CardContent>
        </Card>

        {/* Top Winning Suppliers */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold">Top 5 Proveedores Líderes</CardTitle>
            <CardDescription className="text-xs">
              Monto total adjudicado a los principales oferentes del rubro
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BarRankingChart data={suppliersRanking} height={260} valueIsCurrency={true} />
          </CardContent>
        </Card>
      </div>

      {/* Operational Data Tables Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentTendersTable tenders={recentTenders} />
        <RecentAwardsTable awards={recentAwards} />
      </div>
    </div>
  );
}
