import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Landmark,
  Building2,
  Clock,
  DollarSign,
  Layers,
  ExternalLink,
  FileText,
  Users,
  TrendingUp,
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
import { Badge } from '@/components/ui/badge';
import { useOrganismoDetail } from '@/features/organismos';

export const OrganismoDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: organismo, isLoading, isError } = useOrganismoDetail(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-32 animate-pulse rounded bg-muted/60" />
        <div className="h-40 animate-pulse rounded-xl border border-border/80 bg-card" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-xl border border-border/80 bg-card"
            />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !organismo) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center text-destructive">
        <h2 className="text-lg font-bold text-foreground">Organismo no encontrado</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          No se pudo recuperar la información del perfil del organismo comprador solicitado.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/organismos')}
          className="mt-4 border-border/80 bg-background text-foreground hover:bg-muted"
        >
          Volver al directorio
        </Button>
      </div>
    );
  }

  const getPaymentTermBadge = (days = 30) => {
    let colorClass = 'border-border/80 bg-muted/60 text-muted-foreground';
    let status = 'Estándar';

    if (days <= 30) {
      colorClass = 'border-emerald-500/20 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300';
      status = 'Oportuno (≤ 30 días)';
    } else if (days <= 45) {
      colorClass = 'border-cyan-500/20 bg-cyan-50 text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-300';
      status = 'Dentro de plazo (≤ 45 días)';
    } else {
      colorClass = 'border-amber-500/20 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300';
      status = 'Plazo extendido (> 45 días)';
    }

    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${colorClass}`}
      >
        <Clock className="h-3 w-3" />
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/organismos"
          className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Volver al directorio de organismos compradores</span>
        </Link>
      </div>

      {/* Hero Header Card */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-primary">
                RUT: {formatRUT(organismo.rut)}
              </span>
              <Badge
                variant="outline"
                className="border-emerald-500/20 bg-emerald-50 font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
              >
                {organismo.sector || 'Sector Salud'}
              </Badge>
              <span className="rounded-md border border-border/80 bg-muted/60 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                Código: {organismo.codigo}
              </span>
              {organismo.categoria_principal && (
                <span className="rounded-md border border-border/80 bg-muted/60 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {organismo.categoria_principal}
                </span>
              )}
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              {organismo.nombre || 'Organismo Comprador'}
            </h1>

            <div className="flex flex-wrap items-center gap-4 pt-1 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Landmark className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{organismo.region || 'Región Metropolitana'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Plazo promedio de pago: {organismo.dias_pago_promedio || 30} días</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Executive KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Presupuesto Total Comprado */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Gasto Total Comprado
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <p
            className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-emerald-600 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-emerald-400"
            title={
              organismo.monto_total_comprado
                ? formatCLP(organismo.monto_total_comprado)
                : '$0 CLP'
            }
          >
            {organismo.monto_total_comprado
              ? formatCLP(organismo.monto_total_comprado)
              : '$0 CLP'}
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            Adquisiciones acumuladas
          </span>
        </Card>

        {/* Licitaciones Realizadas */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Licitaciones Totales
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-foreground sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl">
            {organismo.total_licitaciones || 0}
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            {organismo.licitaciones_activas || 0} procesos activos actualmente
          </span>
        </Card>

        {/* Proveedores Contratados */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Proveedores Contratados
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-purple-500/20 bg-purple-50 text-purple-600 dark:bg-purple-950/40 dark:text-purple-400">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-purple-600 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-purple-400">
            {organismo.total_proveedores_contratados || 48}
          </p>
          <span className="mt-1 block truncate text-xs font-medium text-muted-foreground">
            Empresas adjudicatarias
          </span>
        </Card>

        {/* Plazo Pago Promedio */}
        <Card className="min-w-0 rounded-2xl border border-border/80 bg-card p-4 sm:p-5 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Plazo Promedio de Pago
            </span>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-500/20 bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2.5 truncate font-mono text-lg font-bold tracking-tight text-amber-600 sm:text-xl lg:text-lg xl:text-xl 2xl:text-2xl dark:text-amber-400">
            {organismo.dias_pago_promedio || 30} días
          </p>
          <div className="mt-2">{getPaymentTermBadge(organismo.dias_pago_promedio)}</div>
        </Card>
      </div>

      {/* Monthly Purchasing Evolution Chart */}
      {organismo.evolucion_compras && organismo.evolucion_compras.length > 0 && (
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
              <TrendingUp className="h-4 w-4 text-primary" />
              <span>Evolución Mensual del Gasto en Adquisiciones (Últimos 12 Meses)</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={organismo.evolucion_compras}
                  margin={{ top: 10, right: 20, left: 15, bottom: 20 }}
                >
                  <defs>
                    <linearGradient id="colorMontoOrg" x1="0" y1="0" x2="0" y2="1">
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
                          <div className="rounded-lg border border-border/80 bg-popover p-3 text-xs shadow-lg text-popover-foreground">
                            <p className="font-bold">{d.mes}</p>
                            <p className="mt-1 font-mono text-primary font-semibold">
                              Presupuesto: {formatCLP(d.monto)}
                            </p>
                            <p className="mt-0.5 text-muted-foreground">
                              {d.licitaciones} procesos licitatorios
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
                    name="Gasto Mensual (CLP)"
                    stroke="#0d6efd"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorMontoOrg)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Two columns: Top Suppliers & Categories Breakdown */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top Suppliers */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Building2 className="h-4 w-4 text-primary" />
              <span>Ranking de Proveedores Más Contratados</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/60">
              {(organismo.ranking_proveedores || []).map((prov, i) => (
                <div key={i} className="flex items-center justify-between py-2.5 text-xs">
                  <div>
                    <p className="font-semibold text-foreground">{prov.proveedor_nombre}</p>
                    <p className="text-[11px] text-muted-foreground">
                      RUT: {formatRUT(prov.proveedor_rut)} • {prov.contratos} contratos ({prov.porcentaje}%)
                    </p>
                  </div>
                  <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {formatCLP(prov.total_monto)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Categories Breakdown */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Layers className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Desglose de Compras por Rubro</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="space-y-3 pt-1">
              {(organismo.ranking_categorias || []).map((cat, i) => (
                <div key={i} className="space-y-1 text-xs">
                  <div className="flex justify-between text-foreground">
                    <span className="font-medium">{cat.categoria}</span>
                    <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      {cat.porcentaje}% ({formatCLP(cat.total_monto)})
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${cat.porcentaje}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Tenders Table */}
      <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border/80 px-5 py-3.5">
          <h3 className="text-sm font-semibold text-foreground">
            Licitaciones Recientes de este Organismo
          </h3>
          <span className="text-xs text-muted-foreground">
            {organismo.licitaciones_recientes?.length || 0} licitaciones registradas
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-foreground">
            <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Nombre del Proceso</th>
                <th className="px-4 py-3 text-right">Monto Estimado</th>
                <th className="px-4 py-3 text-center">Estado</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 bg-card">
              {(organismo.licitaciones_recientes || []).map((item) => (
                <tr key={item.id} className="group transition-colors hover:bg-muted/40">
                  <td className="px-4 py-3 font-mono font-semibold text-primary">
                    {item.codigo}
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 font-medium text-foreground">
                    {item.nombre}
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {item.monto_estimado ? formatCLP(item.monto_estimado) : 'A convenir'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        item.estado === 'Adjudicada'
                          ? 'border border-emerald-500/20 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                          : item.estado === 'Publicada'
                            ? 'border border-blue-500/20 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
                            : 'border border-border/80 bg-muted/60 text-muted-foreground'
                      }`}
                    >
                      {item.estado || 'Activa'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(item.fecha)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      asChild
                      variant="ghost"
                      size="sm"
                      className="h-7 gap-1 text-xs text-primary hover:bg-primary/10 hover:text-primary"
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
    </div>
  );
};
