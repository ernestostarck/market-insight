import React, { useState } from 'react';
import {
  TrendingUp,
  Users,
  Layers,
  Target,
  DollarSign,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useAdvancedAnalytics,
  MarketOverviewTab,
  SupplierAnalysisTab,
  CategoryAnalysisTab,
  CompetitionAnalysisTab,
  PriceAnalysisTab,
} from '@/features/analytics';

type AnalyticsTab =
  | 'overview'
  | 'suppliers'
  | 'categories'
  | 'competition'
  | 'prices';

export const AnalyticsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AnalyticsTab>('overview');
  const { data, isLoading, isFetching, refetch } = useAdvancedAnalytics();

  const tabs = [
    { id: 'overview' as const, label: 'Visión de Mercado', icon: TrendingUp },
    { id: 'suppliers' as const, label: 'Proveedores & Concentración', icon: Users },
    { id: 'categories' as const, label: 'Rubros & Categorías', icon: Layers },
    { id: 'competition' as const, label: 'Competencia & Descuentos', icon: Target },
    { id: 'prices' as const, label: 'Análisis de Precios Homogéneos', icon: DollarSign },
  ];

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-64 animate-pulse rounded-md bg-muted" />
        <div className="h-12 w-full animate-pulse rounded-lg bg-muted" />
        <div className="h-96 w-full animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Analytics Avanzado & Inteligencia de Precios
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/20 bg-purple-50 px-2.5 py-0.5 text-xs font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-500 animate-pulse" />
                Modelos Cuantitativos
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Series temporales, concentración de mercado, estacionalidad presupuestaria e intensidad competitiva, calculados sobre datos reales de ChileCompra.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-2 border-primary/30 text-primary hover:bg-primary hover:text-white font-medium text-xs rounded-md shadow-sm transition-all"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refrescar</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Analytical Tab Navigation */}
      <div className="flex flex-wrap gap-1.5 rounded-xl border border-border/80 bg-card p-1.5 shadow-sm">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-medium transition-all ${
                isActive
                  ? 'bg-primary/10 text-primary shadow-sm border border-primary/20 font-semibold'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Contents */}
      {activeTab === 'overview' && <MarketOverviewTab data={data.marketOverview} />}
      {activeTab === 'suppliers' && <SupplierAnalysisTab data={data.supplierAnalysis} />}
      {activeTab === 'categories' && <CategoryAnalysisTab data={data.categoryAnalysis} />}
      {activeTab === 'competition' && <CompetitionAnalysisTab data={data.competitionAnalysis} />}
      {activeTab === 'prices' && <PriceAnalysisTab />}
    </div>
  );
};
