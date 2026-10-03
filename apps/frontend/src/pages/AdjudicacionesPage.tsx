import React, { useEffect, useState } from 'react';
import { Search, Award, RefreshCw, X, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  useAdjudicaciones,
  AdjudicacionesTable,
  ADJUDICACION_PAGE_SIZE_OPTIONS,
  type AdjudicacionSortField,
} from '@/features/adjudicaciones';

const SORT_OPTIONS: { value: AdjudicacionSortField; label: string }[] = [
  { value: 'fecha_adjudicacion', label: 'Más recientes' },
  { value: 'monto_adjudicado', label: 'Monto adjudicado' },
  { value: 'proveedor_razon_social', label: 'Proveedor (A-Z)' },
  { value: 'organismo_nombre', label: 'Organismo (A-Z)' },
];

const selectClass =
  'h-10 rounded-md border border-border bg-background px-3 text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40';

export const AdjudicacionesPage: React.FC = () => {
  const {
    data,
    total,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    isLoading,
    isFetching,
    refetch,
    filters,
    setFilters,
    resetFilters,
    sortField,
    sortDirection,
    setSort,
    toggleSort,
  } = useAdjudicaciones();

  // Debounce the search box so the API isn't queried on every keystroke.
  const [search, setSearch] = useState(filters.q ?? '');
  useEffect(() => {
    const id = window.setTimeout(() => {
      if ((filters.q ?? '') !== search) setFilters({ q: search });
    }, 350);
    return () => window.clearTimeout(id);
  }, [search, filters.q, setFilters]);
  useEffect(() => {
    if (!filters.q) setSearch('');
  }, [filters.q]);

  const hasActiveFilters = Boolean(filters.q || filters.monto_min);
  const sortLabel = SORT_OPTIONS.find((o) => o.value === sortField)?.label ?? 'Más recientes';
  const firstIndex = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastIndex = (page - 1) * pageSize + data.length;

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Historial de Adjudicaciones
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                Contratos Públicos
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Registro de ofertas ganadoras, montos adjudicados y márgenes respecto al presupuesto
              referencial en ChileCompra.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-2 rounded-md border-primary/30 text-xs font-medium text-primary shadow-sm transition-all hover:bg-primary hover:text-white"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refrescar</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Buscar por código de licitación, proveedor, RUT u organismo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 rounded-md border-border bg-background pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:ring-primary"
            />
          </div>

          {/* Monto mínimo + ranking + Top N */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:w-auto">
            <select
              value={filters.monto_min ?? 'all'}
              onChange={(e) =>
                setFilters({
                  monto_min: e.target.value === 'all' ? undefined : Number(e.target.value),
                })
              }
              className="h-10 rounded-md border border-border bg-background px-3 text-xs font-semibold text-foreground focus:outline-none focus:ring-primary"
            >
              <option value="all">Monto: Todos</option>
              <option value="30000000">Mayor a $30M CLP</option>
              <option value="50000000">Mayor a $50M CLP</option>
              <option value="100000000">Mayor a $100M CLP</option>
            </select>

            <select
              value={sortField}
              onChange={(e) => {
                const field = e.target.value as AdjudicacionSortField;
                setSort(
                  field,
                  field === 'proveedor_razon_social' || field === 'organismo_nombre'
                    ? 'asc'
                    : 'desc',
                );
              }}
              className={selectClass}
              aria-label="Ordenar por"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  Ordenar: {o.label}
                </option>
              ))}
            </select>

            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className={selectClass}
              aria-label="Cantidad de adjudicaciones a mostrar"
            >
              {ADJUDICACION_PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  Mostrar: Top {n}
                </option>
              ))}
            </select>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
                className="h-10 gap-1 rounded-md text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-950/30"
              >
                <X className="h-3.5 w-3.5" />
                <span>Limpiar</span>
              </Button>
            )}

            <div className="hidden items-center gap-1.5 rounded-md border border-border/80 bg-muted/40 px-3 py-2 text-xs font-medium text-muted-foreground lg:flex">
              <Filter className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>{total.toLocaleString('es-CL')} adjudicaciones</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table Card */}
      <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border/80 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Award className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Top {pageSize} · {sortLabel}
            </span>
          </div>
          {isFetching && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-emerald-500" />
              Sincronizando...
            </span>
          )}
        </div>

        <AdjudicacionesTable
          items={data}
          isLoading={isLoading}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={toggleSort}
        />

        {/* Pagination */}
        <div className="flex flex-col items-center justify-between gap-4 border-t border-border/80 bg-muted/10 px-5 py-3.5 sm:flex-row">
          <div className="text-xs text-muted-foreground">
            Mostrando{' '}
            <strong className="font-semibold text-foreground">
              {firstIndex}–{lastIndex}
            </strong>{' '}
            de{' '}
            <strong className="font-semibold text-foreground">
              {total.toLocaleString('es-CL')}
            </strong>{' '}
            adjudicaciones
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="rounded-md border-border/80 bg-background text-xs font-medium text-foreground shadow-sm hover:bg-muted"
            >
              Anterior
            </Button>
            <span className="px-2 text-xs font-medium text-muted-foreground">
              Página {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="rounded-md border-border/80 bg-background text-xs font-medium text-foreground shadow-sm hover:bg-muted"
            >
              Siguiente
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};
