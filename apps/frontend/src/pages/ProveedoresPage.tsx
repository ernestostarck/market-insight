import React, { useEffect, useState } from 'react';
import {
  Search,
  Building2,
  Users,
  RefreshCw,
  X,
  Filter,
  ShieldCheck,
  Award,
  BarChart3,
  TrendingUp,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  useProveedores,
  useProveedorRubros,
  ProveedoresTable,
  ProveedorComparator,
  PAGE_SIZE_OPTIONS,
  type ProveedorSortField,
} from '@/features/proveedores';
import type { Proveedor } from '@/types';

const SORT_OPTIONS: { value: ProveedorSortField; label: string }[] = [
  { value: 'monto_total_adjudicado', label: 'Monto adjudicado' },
  { value: 'total_adjudicaciones', label: 'N° de adjudicaciones' },
  { value: 'razon_social', label: 'Razón social (A-Z)' },
];

const selectClass =
  'h-10 rounded-md border border-border bg-background px-3 text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40';

/** "Servicios / Construcción / Obras civiles" -> "Obras civiles" (full path stays in the tooltip). */
const lastSegment = (value: string) => value.split(' / ').pop() ?? value;

export const ProveedoresPage: React.FC = () => {
  const [comparatorOpen, setComparatorOpen] = useState(false);
  const [comparatorInitialSuppliers, setComparatorInitialSuppliers] = useState<Proveedor[]>([]);

  const {
    data,
    allItems,
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
  } = useProveedores();
  const { data: rubros = [] } = useProveedorRubros();

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

  const handleOpenComparator = (proveedor?: Proveedor) => {
    if (proveedor) {
      setComparatorInitialSuppliers([proveedor]);
    } else {
      setComparatorInitialSuppliers(allItems.slice(0, 2));
    }
    setComparatorOpen(true);
  };

  const hasActiveFilters = Boolean(filters.q || (filters.rubro && filters.rubro !== 'all'));
  const sortLabel = SORT_OPTIONS.find((o) => o.value === sortField)?.label ?? 'Monto adjudicado';
  const firstIndex = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastIndex = (page - 1) * pageSize + data.length;

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-sm transition-all sm:p-7">
        {/* Ambient Glows */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-blue-500/5 blur-3xl dark:bg-blue-400/10" />
        <div className="pointer-events-none absolute -bottom-16 right-1/3 h-56 w-56 rounded-full bg-indigo-500/5 blur-3xl dark:bg-indigo-400/10" />

        <div className="relative flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          {/* Left: Icon, Title, Badges, Description & Quick Pills */}
          <div className="flex items-start gap-4 sm:gap-5">
            {/* Visual Anchor Icon Badge */}
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20 ring-4 ring-blue-500/10 sm:h-14 sm:w-14">
              <Building2 className="h-6 w-6 text-white sm:h-7 sm:w-7" />
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
                  Directorio de Proveedores
                </h1>
                <span className="shadow-2xs inline-flex items-center gap-1.5 rounded-full border border-blue-200/90 bg-blue-50/90 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-blue-600" />
                  Mercado Público
                </span>
                <span className="shadow-2xs inline-flex items-center gap-1.5 rounded-full border border-emerald-200/90 bg-emerald-50/90 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                  Adjudicatarios Activos
                </span>
                <span className="shadow-2xs inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-100/90 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
                  <Users className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400" />
                  <span>{total > 0 ? `${total} empresas registradas` : 'Directorio Nacional'}</span>
                </span>
              </div>

              <p className="max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                Análisis competitivo de empresas participantes, adjudicaciones acumuladas,
                efectividad comercial y cuota de mercado en compras públicas.
              </p>

              {/* Feature Highlights Strip */}
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-600 dark:text-slate-400">
                <div className="inline-flex items-center gap-1.5 rounded-md border border-slate-200/80 bg-slate-50/80 px-2.5 py-1 font-medium dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300">
                  <Award className="h-3.5 w-3.5 text-amber-500" />
                  <span>Ranking por Monto &amp; Win Rate</span>
                </div>
                <div className="inline-flex items-center gap-1.5 rounded-md border border-slate-200/80 bg-slate-50/80 px-2.5 py-1 font-medium dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300">
                  <BarChart3 className="h-3.5 w-3.5 text-blue-500" />
                  <span>Comparador Head-to-Head</span>
                </div>
                <div className="inline-flex items-center gap-1.5 rounded-md border border-slate-200/80 bg-slate-50/80 px-2.5 py-1 font-medium dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300">
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Historial de Licitaciones</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex flex-wrap items-center gap-2.5 lg:self-start xl:self-center">
            <Button
              variant="default"
              size="sm"
              onClick={() => handleOpenComparator()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm shadow-blue-500/25 transition-all hover:bg-blue-700 active:scale-95"
            >
              <Users className="h-4 w-4" />
              <span>Comparar Proveedores</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              className="shadow-2xs inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-50 hover:text-slate-900 active:scale-95 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <RefreshCw
                className={`h-4 w-4 ${isFetching ? 'animate-spin text-blue-600' : 'text-slate-500 dark:text-slate-400'}`}
              />
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
              placeholder="Buscar por Razón Social, RUT (ej: 76.432.189-5) o nombre de fantasía..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 rounded-md border-border bg-background pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:ring-primary"
            />
          </div>

          {/* Filter Selects */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:w-auto">
            {/* Rubro: real main-award categories from the API */}
            <select
              value={filters.rubro || 'all'}
              onChange={(e) => setFilters({ rubro: e.target.value })}
              className={`${selectClass} max-w-[16rem]`}
              aria-label="Filtrar por rubro principal"
            >
              <option value="all">Rubro: Todos</option>
              {rubros.map((r) => (
                <option key={r.value} value={r.value} title={r.value}>
                  {lastSegment(r.value)} ({r.count})
                </option>
              ))}
            </select>

            {/* Ranking criterion */}
            <select
              value={sortField}
              onChange={(e) => {
                const field = e.target.value as ProveedorSortField;
                setSort(field, field === 'razon_social' ? 'asc' : 'desc');
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

            {/* Top N */}
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className={selectClass}
              aria-label="Cantidad de proveedores a mostrar"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
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
              <Filter className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
              <span>{total} proveedores</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table Card */}
      <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border/80 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Top {pageSize} por {sortLabel.toLowerCase()}
            </span>
          </div>
          {isFetching && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-blue-500" />
              Sincronizando...
            </span>
          )}
        </div>

        <ProveedoresTable
          items={data}
          isLoading={isLoading}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={toggleSort}
          onCompare={handleOpenComparator}
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
            proveedores
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

      {/* Comparison Modal */}
      <ProveedorComparator
        isOpen={comparatorOpen}
        initialSuppliers={comparatorInitialSuppliers}
        onClose={() => setComparatorOpen(false)}
      />
    </div>
  );
};
