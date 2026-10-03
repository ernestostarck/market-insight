import React from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  Landmark,
  TrendingUp,
  Tag,
  ExternalLink,
  Layers,
  Building2,
  FileText,
  DollarSign,
  Users,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { formatCLP, formatRUT, formatCompactCurrency } from '@/lib/formatters';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useMarketObjective } from '@/features/analytics';
import { setSegmento, useSegmento } from '@/features/segmento';

export const MarketObjectivePage: React.FC = () => {
  const { data, isLoading, isError, refetch, isFetching } = useMarketObjective();
  const segmento = useSegmento();
  const isConcept = segmento?.code.startsWith('concept:') ?? false;

  if (isError && !data) {
    return (
      <div className="rounded-xl border border-border/80 bg-card p-6 text-sm shadow-sm">
        <p className="font-semibold text-foreground">No se pudo cargar el Mercado Objetivo.</p>
        <p className="mt-1 text-muted-foreground">
          El servidor no respondió a tiempo o devolvió un error.
        </p>
        <Button
          size="sm"
          variant="outline"
          className="mt-4"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? 'Reintentando…' : 'Reintentar'}
        </Button>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-64 animate-pulse rounded-lg bg-muted" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-lg border border-border bg-card shadow-sm"
            />
          ))}
        </div>
      </div>
    );
  }

  const {
    kpis,
    tasa_crecimiento,
    tendencias,
    organismos_lideres,
    proveedores_lideres,
    categorias_relacionadas,
  } = data;

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                {segmento
                  ? `Mercado: ${segmento.label}`
                  : 'Mercado Objetivo: Discapacidad & Geriatría'}
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                {segmento
                  ? isConcept
                    ? `Concepto${segmento.parentLabel ? ` · ${segmento.parentLabel}` : ''}`
                    : 'Rubro seleccionado'
                  : 'Nicho Principal'}
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              {segmento ? (
                <>
                  Licitaciones cuyo nombre o descripción coincide con los términos del{' '}
                  {isConcept ? 'concepto' : 'rubro'} «{segmento.label}» (
                  {data.dictionary_terms_used} términos), con sus montos y actores adjudicados.
                </>
              ) : (
                <>
                  Licitaciones cuyo nombre o descripción coincide con el diccionario de dominio
                  geriatría/discapacidad ({data.dictionary_terms_used} términos reales), con sus
                  montos y actores adjudicados.
                </>
              )}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2.5">
            {segmento ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSegmento(null)}
                className="rounded-md text-xs font-semibold"
              >
                Volver a Geriatría &amp; Discapacidad
              </Button>
            ) : (
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="rounded-md text-xs font-semibold"
              >
                <Link to="/rubros">Cambiar rubro</Link>
              </Button>
            )}
            <Button
              asChild
              variant="outline"
              size="sm"
              className="rounded-md border-primary/30 text-xs font-semibold text-primary shadow-sm transition-all hover:bg-primary hover:text-white"
            >
              <Link to="/analytics" className="inline-flex items-center gap-1.5">
                <span>Ver Analytics Completo</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {kpis.licitaciones_relacionadas === 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-50 p-4 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
          Aún no hay licitaciones en la base de datos que coincidan con los términos de este{' '}
          {isConcept ? 'concepto' : 'rubro'}. Los indicadores se completarán a medida que el ETL
          cargue procesos del rubro.
        </div>
      )}

      {/* 6 Executive KPI Cards in Bootstrap 5.3 Style */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
        {/* Licitaciones */}
        <Card className="flex flex-col justify-between rounded-lg border-border/80 bg-card p-4 shadow-sm transition-all hover:shadow-md">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Licitaciones
              </span>
              <div className="rounded-md bg-blue-50 p-1.5 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
                <FileText className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 font-mono text-2xl font-bold tracking-tight text-foreground">
              {kpis.licitaciones_relacionadas}
            </p>
          </div>
          <span className="mt-2 block text-[11px] text-muted-foreground">Procesos específicos</span>
        </Card>

        {/* Monto Total */}
        <Card className="flex flex-col justify-between rounded-lg border-border/80 bg-card p-4 shadow-sm transition-all hover:shadow-md">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Monto Transado
              </span>
              <div className="rounded-md bg-emerald-50 p-1.5 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400">
                <DollarSign className="h-4 w-4" />
              </div>
            </div>
            <p
              className="mt-2 truncate font-mono text-lg font-bold tracking-tight text-emerald-600 dark:text-emerald-400 xl:text-xl"
              title={formatCLP(kpis.monto_total)}
            >
              {formatCLP(kpis.monto_total)}
            </p>
          </div>
          <span className="mt-2 block text-[11px] text-muted-foreground">Gasto público total</span>
        </Card>

        {/* Proveedores Activos */}
        <Card className="flex flex-col justify-between rounded-lg border-border/80 bg-card p-4 shadow-sm transition-all hover:shadow-md">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Proveedores
              </span>
              <div className="rounded-md bg-cyan-50 p-1.5 text-cyan-600 dark:bg-cyan-950/50 dark:text-cyan-400">
                <Users className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 font-mono text-2xl font-bold tracking-tight text-cyan-600 dark:text-cyan-400">
              {kpis.proveedores_activos}
            </p>
          </div>
          <span className="mt-2 block text-[11px] text-muted-foreground">
            Adjudicatarios del rubro
          </span>
        </Card>

        {/* Organismos Compradores */}
        <Card className="flex flex-col justify-between rounded-lg border-border/80 bg-card p-4 shadow-sm transition-all hover:shadow-md">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Organismos
              </span>
              <div className="rounded-md bg-indigo-50 p-1.5 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
                <Building2 className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 font-mono text-2xl font-bold tracking-tight text-indigo-600 dark:text-indigo-400">
              {kpis.organismos_activos}
            </p>
          </div>
          <span className="mt-2 block text-[11px] text-muted-foreground">
            Entidades demandantes
          </span>
        </Card>

        {/* Precio Promedio Ponderado */}
        <Card className="flex flex-col justify-between rounded-lg border-border/80 bg-card p-4 shadow-sm transition-all hover:shadow-md">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Precio Promedio
              </span>
              <div className="rounded-md bg-amber-50 p-1.5 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400">
                <Tag className="h-4 w-4" />
              </div>
            </div>
            <p
              className="mt-2 truncate font-mono text-lg font-bold tracking-tight text-amber-600 dark:text-amber-400 xl:text-xl"
              title={kpis.precio_promedio != null ? formatCLP(kpis.precio_promedio) : undefined}
            >
              {kpis.precio_promedio != null ? formatCLP(kpis.precio_promedio) : '—'}
            </p>
          </div>
          <span className="mt-2 block text-[11px] text-muted-foreground">
            Por unidad asistencial
          </span>
        </Card>

        {/* Crecimiento mes a mes */}
        <Card className="flex flex-col justify-between rounded-lg border-border/80 bg-card p-4 shadow-sm transition-all hover:shadow-md">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Crecimiento Mensual
              </span>
              <div
                className={`rounded-md p-1.5 ${
                  (tasa_crecimiento ?? 0) >= 0
                    ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400'
                    : 'bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400'
                }`}
              >
                <TrendingUp className="h-4 w-4" />
              </div>
            </div>
            <div
              className={`mt-2 flex items-center gap-1 font-mono text-2xl font-bold tracking-tight ${
                (tasa_crecimiento ?? 0) >= 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-red-600 dark:text-red-400'
              }`}
            >
              <span>
                {tasa_crecimiento != null
                  ? `${tasa_crecimiento > 0 ? '+' : ''}${tasa_crecimiento}%`
                  : '—'}
              </span>
            </div>
          </div>
          <span className="mt-2 block text-[11px] text-muted-foreground">
            Último mes vs. mes anterior
          </span>
        </Card>
      </div>

      {/* Monthly Demand Trend Chart */}
      <Card className="rounded-lg border-border/80 bg-card p-6 shadow-sm">
        <CardHeader className="p-0 pb-5">
          <CardTitle className="flex items-center gap-2 text-base font-bold text-foreground">
            <Activity className="h-4 w-4 text-primary" />
            <span>
              Curva de Demanda Mensual en{' '}
              {segmento ? segmento.label : 'Ayudas Técnicas y Geriatría'}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={tendencias} margin={{ top: 10, right: 20, left: 15, bottom: 20 }}>
                <defs>
                  <linearGradient id="colorMontoTarget" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d6efd" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0d6efd" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" vertical={false} />
                <XAxis dataKey="mes" stroke="#6c757d" tick={{ fontSize: 11 }} />
                <YAxis
                  stroke="#6c757d"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => formatCompactCurrency(v)}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="rounded-lg border border-border bg-card p-3 text-xs text-foreground shadow-lg">
                          <p className="font-bold text-foreground">{d.mes}</p>
                          <p className="mt-1 font-mono font-semibold text-primary">
                            Gasto: {formatCLP(d.monto)}
                          </p>
                          <p className="mt-0.5 text-muted-foreground">
                            {d.licitaciones} licitaciones del rubro
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
                  name="Gasto Mensual"
                  stroke="#0d6efd"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#colorMontoTarget)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Two columns: Leading Buyers and Leading Suppliers */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Leading Organismos */}
        <Card className="rounded-lg border-border/80 bg-card p-6 shadow-sm">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-foreground">
              <Landmark className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Principales Organismos Compradores {segmento ? 'del Rubro' : 'del Nicho'}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {organismos_lideres.map((org, i) => (
                <div key={i} className="flex items-center justify-between py-3 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">{org.nombre}</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      {org.contratos} licitaciones ({org.porcentaje}%)
                    </p>
                  </div>
                  <span className="font-mono font-bold text-primary">
                    {formatCLP(org.monto_total)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Leading Suppliers */}
        <Card className="rounded-lg border-border/80 bg-card p-6 shadow-sm">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-foreground">
              <Building2 className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
              <span>Proveedores Especializados Líderes</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {proveedores_lideres.map((prov, i) => (
                <div key={i} className="flex items-center justify-between py-3 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">{prov.nombre}</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      RUT: {prov.rut ? formatRUT(prov.rut) : '-'} • {prov.contratos} contratos (
                      {prov.porcentaje}%)
                    </p>
                  </div>
                  <span className="font-mono font-bold text-cyan-600 dark:text-cyan-400">
                    {formatCLP(prov.monto_total)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Related Categories */}
      <Card className="rounded-lg border-border/80 bg-card p-6 shadow-sm">
        <CardHeader className="p-0 pb-4">
          <CardTitle className="flex items-center gap-2 text-sm font-bold text-foreground">
            <Layers className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span>Categorías Relacionadas</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 p-0 pt-1">
          {categorias_relacionadas.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Sin categorías asignadas todavía entre las licitaciones{' '}
              {segmento ? 'del rubro' : 'del nicho'}.
            </p>
          )}
          {categorias_relacionadas.map((cat, i) => (
            <div key={i} className="space-y-1.5 text-xs">
              <div className="flex justify-between text-foreground">
                <span className="font-medium">
                  {cat.codigo && (
                    <span className="font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                      {cat.codigo}
                    </span>
                  )}{' '}
                  {cat.nombre ?? 'Sin categoría'}
                </span>
                <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                  {cat.porcentaje}% ({formatCLP(cat.monto)})
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-600 to-emerald-500"
                  style={{ width: `${cat.porcentaje}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};
