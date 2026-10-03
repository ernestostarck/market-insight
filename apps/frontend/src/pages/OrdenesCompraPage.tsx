import React from 'react';
import { Search, ShoppingBag, RefreshCw, X, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useOrdenesCompra, OrdenesCompraTable } from '@/features/adjudicaciones';

export const OrdenesCompraPage: React.FC = () => {
  const {
    data,
    total,
    page,
    setPage,
    totalPages,
    isLoading,
    isFetching,
    refetch,
    filters,
    setFilters,
    resetFilters,
    sortField,
    sortDirection,
    toggleSort,
  } = useOrdenesCompra();

  const hasActiveFilters = Boolean(filters.q || (filters.estado && filters.estado !== 'all'));

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Órdenes de Compra
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/20 bg-cyan-50 px-2.5 py-0.5 text-xs font-semibold text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-300">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" />
                Ejecución Transaccional
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Trazabilidad de órdenes emitidas por organismos públicos, estado de recepción y facturación asociada a licitaciones.
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

      {/* Filter Bar */}
      <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Buscar por código de OC (ej: 1057416-24-OC1), proveedor u organismo..."
              value={filters.q || ''}
              onChange={(e) => setFilters({ q: e.target.value })}
              className="h-10 rounded-md border-border bg-background pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:ring-primary"
            />
          </div>

          {/* Estado Filter */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:w-auto">
            <select
              value={filters.estado || 'all'}
              onChange={(e) => setFilters({ estado: e.target.value })}
              className="h-10 rounded-md border border-border bg-background px-3 text-xs font-semibold text-foreground focus:ring-primary focus:outline-none"
            >
              <option value="all">Estado: Todos</option>
              <option value="Aceptada">Aceptada</option>
              <option value="Recepcionada">Recepcionada</option>
              <option value="Facturada">Facturada</option>
              <option value="Pagada">Pagada</option>
            </select>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
                className="h-10 gap-1 text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-950/30 rounded-md"
              >
                <X className="h-3.5 w-3.5" />
                <span>Limpiar</span>
              </Button>
            )}

            <div className="hidden items-center gap-1.5 rounded-md border border-border/80 bg-muted/40 px-3 py-2 text-xs font-medium text-muted-foreground lg:flex">
              <Filter className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" />
              <span>{total} órdenes</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table Card */}
      <Card className="overflow-hidden border border-border/80 bg-card shadow-sm rounded-xl">
        <div className="flex items-center justify-between border-b border-border/80 px-5 py-3.5 bg-muted/20">
          <div className="flex items-center gap-2">
            <ShoppingBag className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Listado de Órdenes de Compra Emitidas
            </span>
          </div>
          {isFetching && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-cyan-500" />
              Sincronizando...
            </span>
          )}
        </div>

        <OrdenesCompraTable
          items={data}
          isLoading={isLoading}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={toggleSort}
        />

        {/* Pagination */}
        <div className="flex flex-col items-center justify-between gap-4 border-t border-border/80 px-5 py-3.5 bg-muted/10 sm:flex-row">
          <div className="text-xs text-muted-foreground">
            Mostrando <strong className="text-foreground font-semibold">{data.length}</strong> de{' '}
            <strong className="text-foreground font-semibold">{total}</strong> órdenes registradas
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="border-border/80 bg-background text-foreground hover:bg-muted text-xs font-medium rounded-md shadow-sm"
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
              className="border-border/80 bg-background text-foreground hover:bg-muted text-xs font-medium rounded-md shadow-sm"
            >
              Siguiente
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};
