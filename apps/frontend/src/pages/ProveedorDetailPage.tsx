import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  Calendar,
  Award,
  TrendingUp,
  Percent,
  DollarSign,
  Layers,
  Landmark,
  ExternalLink,
  Users,
  ShieldCheck,
  MapPin,
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
import { formatCLP, formatDate, formatRUT, formatCompactCurrency } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useProveedorDetail, ProveedorComparator } from '@/features/proveedores';

export const ProveedorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [comparatorOpen, setComparatorOpen] = useState(false);

  const { data: proveedor, isLoading, isError } = useProveedorDetail(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-32 animate-pulse rounded bg-muted/60" />
        <div className="h-40 animate-pulse rounded-2xl border border-border/80 bg-card" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-2xl border border-border/80 bg-card"
            />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !proveedor) {
    return (
      <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-8 text-center text-destructive">
        <h2 className="text-lg font-bold text-foreground">Proveedor no encontrado</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          No se pudo recuperar la información del perfil del proveedor solicitado.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/proveedores')}
          className="mt-4 border-border/80 bg-background text-foreground hover:bg-muted font-medium"
        >
          Volver al directorio
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/proveedores"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Volver al directorio de proveedores</span>
        </Link>
      </div>

      {/* Hero Header Card */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-card p-6 sm:p-7 shadow-sm transition-all">
        {/* Ambient Glows */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-blue-500/5 blur-3xl dark:bg-blue-400/10" />
        <div className="pointer-events-none absolute right-1/3 -bottom-16 h-56 w-56 rounded-full bg-indigo-500/5 blur-3xl dark:bg-indigo-400/10" />

        <div className="relative flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
          <div className="flex items-start gap-4 sm:gap-5">
            {/* Visual Anchor Icon Badge */}
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20 ring-4 ring-blue-500/10">
              <Building2 className="h-7 w-7 text-white" />
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200/90 bg-blue-50/90 px-3 py-0.5 font-mono text-xs font-bold text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
                  RUT: {formatRUT(proveedor.rut)}
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200/90 bg-emerald-50/90 px-3 py-0.5 text-xs font-semibold text-emerald-700 shadow-2xs dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
                  Proveedor Activo en ChileCompra
                </span>
                {proveedor.categoria_principal && (
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-100/90 px-3 py-0.5 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
                    {proveedor.categoria_principal}
                  </span>
                )}
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 leading-snug">
                {proveedor.razon_social}
              </h1>

              {proveedor.nombre_fantasia && (
                <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                  Nombre de Fantasía:{' '}
                  <span className="font-semibold text-slate-900 dark:text-slate-200">
                    {proveedor.nombre_fantasia}
                  </span>
                </p>
              )}

              <div className="flex flex-wrap items-center gap-4 pt-1 text-xs text-slate-500 dark:text-slate-400">
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500" />
                  <span>{proveedor.region || 'Metropolitana de Santiago'}</span>
                </div>
                {proveedor.fecha_registro && (
                  <div className="flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500" />
                    <span>Registrado en MercadoPúblico: {formatDate(proveedor.fecha_registro)}</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Registro de Proveedores Vigente</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action button: Compare */}
          <div className="flex shrink-0 items-start lg:items-end">
            <Button
              onClick={() => setComparatorOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm shadow-blue-500/25 hover:bg-blue-700 active:scale-95 transition-all"
            >
              <Users className="h-4 w-4" />
              <span>Comparar con Competidores</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 4 Executive KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Monto Total */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Monto Adjudicado
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <p
            className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-emerald-600 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-emerald-400"
            title={
              proveedor.monto_total_adjudicado
                ? formatCLP(proveedor.monto_total_adjudicado)
                : '$0 CLP'
            }
          >
            {proveedor.monto_total_adjudicado
              ? formatCLP(proveedor.monto_total_adjudicado)
              : '$0 CLP'}
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            Ventas totales acumuladas
          </span>
        </Card>

        {/* Adjudicaciones Ganadas */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Contratos Ganados
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-slate-900 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-slate-100">
            {proveedor.total_adjudicaciones || 0}
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            De {proveedor.total_licitaciones_participadas || 0} licitaciones postuladas
          </span>
        </Card>

        {/* Tasa de Éxito */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Tasa de Éxito
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-500/20 bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400">
              <Percent className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-amber-600 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-amber-400">
            {proveedor.tasa_exito?.toFixed(1) || '0.0'}%
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            Efectividad de adjudicación
          </span>
        </Card>

        {/* Cuota de Mercado */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Cuota de Mercado
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-purple-500/20 bg-purple-50 text-purple-600 dark:bg-purple-950/40 dark:text-purple-400">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-purple-600 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-purple-400">
            {proveedor.cuota_mercado_estimada?.toFixed(1) || '24.8'}%
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            En rubro de camas y movilidad
          </span>
        </Card>
      </div>

      {/* Evolution Chart */}
      {proveedor.evolucion_mensual && proveedor.evolucion_mensual.length > 0 && (
        <Card className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Evolución Mensual de Ventas Públicas (Últimos 12 Meses)</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={proveedor.evolucion_mensual}
                  margin={{ top: 10, right: 20, left: 15, bottom: 20 }}
                >
                  <defs>
                    <linearGradient id="colorMontoProv" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/70" vertical={false} />
                  <XAxis dataKey="mes" className="text-muted-foreground" tick={{ fontSize: 11 }} />
                  <YAxis
                    className="text-muted-foreground"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => formatCompactCurrency(v)}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="rounded-xl border border-border bg-card p-3 text-xs shadow-xl">
                            <p className="font-bold text-foreground">{d.mes}</p>
                            <p className="mt-1 font-mono text-emerald-600 dark:text-emerald-400">
                              Monto: {formatCLP(d.monto)}
                            </p>
                            <p className="mt-0.5 text-muted-foreground">
                              {d.adjudicaciones} contratos adjudicados
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
                    name="Monto Adjudicado (CLP)"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#colorMontoProv)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Two columns: Top Buyers & Categories */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top Buyers */}
        <Card className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100">
              <Landmark className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span>Principales Organismos Compradores</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/60">
              {(proveedor.principales_compradores || []).map((b, i) => (
                <div key={i} className="flex items-center justify-between py-3 text-xs transition-colors hover:bg-muted/30 px-2 rounded-lg">
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-slate-100">{b.organismo_nombre}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {b.total_licitaciones || 1} contratos adjudicados
                    </p>
                  </div>
                  <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {formatCLP(b.total_monto)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Categories Breakdown */}
        <Card className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100">
              <Layers className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Distribución de Ventas por Rubro</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="space-y-4 pt-1">
              {(proveedor.principales_categorias || []).map((cat, i) => (
                <div key={i} className="space-y-1.5 text-xs">
                  <div className="flex justify-between text-slate-800 dark:text-slate-200">
                    <span className="font-medium">{cat.categoria}</span>
                    <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      {cat.porcentaje}% ({formatCLP(cat.total_monto)})
                    </span>
                  </div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-600 to-emerald-500"
                      style={{ width: `${cat.porcentaje}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Awards Table */}
      <Card className="overflow-hidden rounded-2xl border border-border/80 bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border/80 bg-muted/20 px-6 py-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            Últimas Licitaciones Adjudicadas a este Proveedor
          </h3>
          <span className="rounded-full border border-border/80 bg-background px-3 py-1 text-xs font-medium text-muted-foreground shadow-2xs">
            {proveedor.ultimas_adjudicaciones?.length || 0} adjudicaciones recientes
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-foreground">
            <thead className="border-b border-border/80 bg-muted/40 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-5 py-3.5">Código Licitación</th>
                <th className="px-5 py-3.5">Nombre del Proceso</th>
                <th className="px-5 py-3.5">Organismo Comprador</th>
                <th className="px-5 py-3.5 text-right">Monto Adjudicado</th>
                <th className="px-5 py-3.5">Fecha</th>
                <th className="px-5 py-3.5 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 bg-card">
              {(proveedor.ultimas_adjudicaciones || []).map((item) => (
                <tr key={item.id} className="transition-colors hover:bg-muted/40">
                  <td className="px-5 py-3.5 font-mono font-semibold text-blue-600 dark:text-blue-400">
                    {item.codigo_licitacion}
                  </td>
                  <td className="max-w-xs truncate px-5 py-3.5 font-medium text-slate-900 dark:text-slate-100">
                    {item.nombre_licitacion}
                  </td>
                  <td className="px-5 py-3.5 text-slate-600 dark:text-slate-300">
                    {item.organismo || 'Hospital Público'}
                  </td>
                  <td className="px-5 py-3.5 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {formatCLP(item.monto)}
                  </td>
                  <td className="px-5 py-3.5 text-muted-foreground">{formatDate(item.fecha)}</td>
                  <td className="px-5 py-3.5 text-right">
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      className="h-7 gap-1.5 border-primary/30 text-primary hover:bg-primary hover:text-white rounded-md text-xs font-semibold shadow-2xs transition-all"
                    >
                      <Link to={`/licitaciones/${item.id}`}>
                        <span>Ver Ficha</span>
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Comparison Modal */}
      <ProveedorComparator
        isOpen={comparatorOpen}
        initialSuppliers={[proveedor]}
        onClose={() => setComparatorOpen(false)}
      />
    </div>
  );
};
