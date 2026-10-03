import React from 'react';
import { DollarSign, Info, TrendingUp, Tag, Search } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { formatCLP, formatDate, formatCompactCurrency } from '@/lib/formatters';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { usePriceAnalysis } from '../hooks/usePriceAnalysis';

export const PriceAnalysisTab: React.FC = () => {
  const { filters, setFilters, isLoading, hasSearched, stats } = usePriceAnalysis();

  return (
    <div className="space-y-6">
      {/* Free-text product search — core.licitacion_item has no brand/material/capacity
          columns, so unlike a fixed catalog, matching is by real item name/description. */}
      <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
        <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Buscar producto adjudicado (ej: cama clínica eléctrica, silla de ruedas)
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={filters.q}
            onChange={(e) => setFilters({ q: e.target.value })}
            placeholder="Escribe al menos 2 caracteres..."
            className="h-10 w-full rounded-md border border-border bg-background pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {!hasSearched ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-border/80 bg-card p-12 text-center">
          <Search className="mb-3 h-10 w-10 text-muted-foreground/60" />
          <p className="text-sm text-muted-foreground">
            Escribe el nombre de un producto para comparar precios unitarios adjudicados reales.
          </p>
        </div>
      ) : isLoading ? (
        <div className="h-40 animate-pulse rounded-xl border border-border/80 bg-card" />
      ) : stats.total_muestras === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-border/80 bg-card p-12 text-center">
          <Info className="mb-3 h-10 w-10 text-muted-foreground/60" />
          <p className="text-sm text-muted-foreground">
            No se encontraron ítems adjudicados con precio unitario que coincidan con "{filters.q}".
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-start gap-2.5 rounded-lg border border-border/80 bg-muted/40 p-3 text-xs font-medium text-muted-foreground">
            <Info className="h-4 w-4 shrink-0 mt-0.5" />
            <span>
              Coincidencia por texto libre sobre el nombre/descripción real del ítem — no hay marca,
              modelo ni capacidad registrados en ChileCompra para verificar homogeneidad técnica exacta.
              Revisa la tabla de muestras para confirmar que son comparables.
            </span>
          </div>

          {/* 4 Statistical Metric Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Precio Mínimo Adjudicado
              </span>
              <p className="mt-3 font-mono text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {formatCLP(stats.precio_minimo)}
              </p>
              <span className="mt-1 block text-xs text-muted-foreground">Menor valor adjudicado registrado</span>
            </Card>

            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Precio Mediano (P50)
              </span>
              <p className="mt-3 font-mono text-2xl font-bold text-primary">
                {formatCLP(stats.precio_mediano)}
              </p>
              <span className="mt-1 block text-xs text-muted-foreground">Mediana de la muestra encontrada</span>
            </Card>

            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Precio Promedio
              </span>
              <p className="mt-3 font-mono text-2xl font-bold text-foreground">
                {formatCLP(stats.precio_promedio)}
              </p>
              <span className="mt-1 block text-xs text-muted-foreground">
                Desv. Estándar: ±{formatCLP(stats.desviacion_estandar)}
              </span>
            </Card>

            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Precio Máximo Adjudicado
              </span>
              <p className="mt-3 font-mono text-2xl font-bold text-amber-600 dark:text-amber-400">
                {formatCLP(stats.precio_maximo)}
              </p>
              <span className="mt-1 block text-xs text-muted-foreground">
                Muestras analizadas: {stats.total_muestras} ítems
              </span>
            </Card>
          </div>

          {/* Distribution Chart & Historical Trend */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <CardHeader className="p-0 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Distribución de Precios Unitarios (Histograma)</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-56 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={stats.distribucion} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis dataKey="rango" stroke="#64748b" tick={{ fontSize: 10 }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload;
                            return (
                              <div className="rounded-lg border border-border/80 bg-popover p-2.5 text-xs shadow-xl text-popover-foreground">
                                <p className="font-bold">{d.rango}</p>
                                <p className="mt-1 font-mono text-primary font-semibold">
                                  {d.count} ítems adjudicados
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar dataKey="count" fill="#0d6efd" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <CardHeader className="p-0 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <span>Evolución Temporal del Precio Unitario Promedio</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-56 w-full pt-2">
                  {stats.evolucion_temporal.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                      Sin fechas de publicación registradas en esta muestra.
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={stats.evolucion_temporal}
                        margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                        <XAxis dataKey="fecha" stroke="#64748b" tick={{ fontSize: 11 }} />
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
                                  <p className="font-bold">{d.fecha}</p>
                                  <p className="mt-1 font-mono text-primary font-semibold">
                                    Promedio: {formatCLP(d.precio_promedio)}
                                  </p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Bar dataKey="precio_promedio" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Real line items */}
          <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
            <CardHeader className="border-b border-border/80 p-4">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Tag className="h-4 w-4 text-primary" />
                <span>Ítems Adjudicados Encontrados ({stats.items.length} registros)</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-foreground">
                  <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3">Licitación</th>
                      <th className="px-4 py-3">Organismo</th>
                      <th className="px-4 py-3">Ítem</th>
                      <th className="px-4 py-3">Categoría</th>
                      <th className="px-4 py-3 text-right">Precio Unitario</th>
                      <th className="px-4 py-3 text-center">Cantidad</th>
                      <th className="px-4 py-3 text-center">Fecha</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60 bg-card">
                    {stats.items.map((item, idx) => (
                      <tr key={idx} className="group transition-colors hover:bg-muted/40">
                        <td className="whitespace-nowrap px-4 py-3 font-mono font-semibold text-primary">
                          {item.licitacion_codigo ?? '—'}
                        </td>
                        <td className="max-w-xs truncate px-4 py-3 text-foreground">
                          {item.organismo ?? '—'}
                        </td>
                        <td className="max-w-sm px-4 py-3 text-foreground">{item.nombre ?? '—'}</td>
                        <td className="px-4 py-3 text-[11px] text-muted-foreground">
                          {item.categoria_nombre ?? '—'}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                          {item.precio_unitario != null ? formatCLP(Number(item.precio_unitario)) : '—'}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-center font-mono text-muted-foreground">
                          {item.cantidad ?? '—'} {item.unidad ?? ''}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-center text-muted-foreground">
                          {item.fecha ? formatDate(item.fecha) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};
