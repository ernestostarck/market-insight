import React, { useEffect, useState } from 'react';
import {
  Search,
  FolderTree,
  RefreshCw,
  X,
  Filter,
  Building2,
  Landmark,
  AlertTriangle,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { formatCLP, formatRUT } from '@/lib/formatters';
import {
  useCategorias,
  CategoriasTable,
  CATEGORIA_PAGE_SIZE_OPTIONS,
  type CategoriaSortField,
} from '@/features/categorias';

const SORT_OPTIONS: { value: CategoriaSortField; label: string }[] = [
  { value: 'monto_total', label: 'Monto adjudicado' },
  { value: 'total_licitaciones', label: 'N° de licitaciones' },
  { value: 'total_proveedores', label: 'N° de proveedores' },
  { value: 'codigo', label: 'Código' },
  { value: 'nombre', label: 'Nombre (A-Z)' },
];

const selectClass =
  'h-10 rounded-md border border-border bg-background px-3 text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40';

export const CategoriasPage: React.FC = () => {
  const {
    items,
    total,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    setSort,
    isLoading,
    isFetching,
    isError,
    refetch,
    filters,
    setFilters,
    resetFilters,
    sortField,
    sortDirection,
    toggleSort,
    selectedCategoria,
    isDetailLoading,
    openCategoriaDetail,
    closeCategoriaDetail,
  } = useCategorias();

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

  const hasActiveFilters = Boolean(filters.q || filters.monto_minimo);
  const sortLabel = SORT_OPTIONS.find((o) => o.value === sortField)?.label ?? 'Monto adjudicado';
  const firstIndex = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastIndex = (page - 1) * pageSize + items.length;

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Rubros ChileCompra
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/20 bg-purple-50 px-2.5 py-0.5 text-xs font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-purple-500" />
                Datos reales
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Rubros tal como los publica ChileCompra en cada licitación, con licitaciones, monto
              adjudicado, proveedores y compradores calculados en tiempo real.
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
              placeholder="Buscar por código o nombre de rubro..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 rounded-md border-border bg-background pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:ring-primary"
            />
          </div>

          {/* Ranking criterion + Top N */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:w-auto">
            <select
              value={sortField}
              onChange={(e) => {
                const field = e.target.value as CategoriaSortField;
                setSort(field, field === 'codigo' || field === 'nombre' ? 'asc' : 'desc');
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
              aria-label="Cantidad de rubros a mostrar"
            >
              {CATEGORIA_PAGE_SIZE_OPTIONS.map((n) => (
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
              <Filter className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400" />
              <span>{total.toLocaleString('es-CL')} rubros</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table Card */}
      <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border/80 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <FolderTree className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Top {pageSize} por {sortLabel.toLowerCase()}
            </span>
          </div>
          {isFetching && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-purple-500" />
              Sincronizando...
            </span>
          )}
        </div>

        {isError ? (
          <div className="flex flex-col items-center justify-center gap-2 p-12 text-center">
            <AlertTriangle className="h-10 w-10 text-amber-500" />
            <h3 className="text-sm font-semibold text-foreground">No se pudo cargar los rubros</h3>
            <p className="max-w-md text-xs text-muted-foreground">
              La API de rubros no respondió. Reintenta con "Refrescar".
            </p>
          </div>
        ) : (
          <CategoriasTable
            items={items}
            isLoading={isLoading}
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={toggleSort}
            onSelectCategoria={openCategoriaDetail}
          />
        )}

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
            rubros
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

      {/* Category Detail Modal */}
      {selectedCategoria !== null || isDetailLoading ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl">
            {isDetailLoading || !selectedCategoria ? (
              <div className="flex flex-col items-center justify-center gap-3 p-10 text-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <p className="text-xs text-muted-foreground">Cargando detalle del rubro...</p>
              </div>
            ) : (
              <>
                {/* Modal Header */}
                <div className="flex items-start justify-between border-b border-border pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      {selectedCategoria.codigo && (
                        <span className="font-mono text-sm font-bold text-emerald-600 dark:text-emerald-400">
                          {selectedCategoria.codigo}
                        </span>
                      )}
                    </div>
                    {(selectedCategoria.segmento || selectedCategoria.familia) && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {[selectedCategoria.segmento, selectedCategoria.familia]
                          .filter(Boolean)
                          .join(' / ')}
                      </p>
                    )}
                    <h2 className="mt-1 text-xl font-bold text-foreground">
                      {selectedCategoria.clase ?? selectedCategoria.nombre ?? 'Sin nombre'}
                    </h2>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={closeCategoriaDetail}
                    className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* Quick KPIs */}
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-border/80 bg-muted/30 p-3">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Monto Adjudicado
                    </span>
                    <p className="mt-1 font-mono text-base font-bold text-emerald-600 dark:text-emerald-400">
                      {formatCLP(selectedCategoria.monto_total)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/80 bg-muted/30 p-3">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Licitaciones
                    </span>
                    <p className="mt-1 font-mono text-base font-bold text-foreground">
                      {selectedCategoria.total_licitaciones}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/80 bg-muted/30 p-3">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Proveedores Activos
                    </span>
                    <p className="mt-1 font-mono text-base font-bold text-cyan-600 dark:text-cyan-400">
                      {selectedCategoria.total_proveedores}
                    </p>
                  </div>
                </div>

                {/* Two columns: Top Suppliers & Top Buyers */}
                <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {/* Suppliers */}
                  <Card className="border border-border/80 bg-card p-4 shadow-sm">
                    <CardHeader className="p-0 pb-3">
                      <CardTitle className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        <Building2 className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" />
                        <span>Proveedores con Mayor Cuota</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      {selectedCategoria.principales_proveedores.length === 0 ? (
                        <p className="py-4 text-center text-xs text-muted-foreground">
                          Sin adjudicaciones registradas todavía.
                        </p>
                      ) : (
                        <div className="divide-y divide-border/60">
                          {selectedCategoria.principales_proveedores.map((prov) => (
                            <div key={prov.proveedor_id} className="py-2 text-xs">
                              <div className="flex justify-between font-semibold text-foreground">
                                <span className="truncate pr-2">
                                  {prov.proveedor_nombre ?? 'Sin nombre'}
                                </span>
                                <span className="font-mono text-cyan-600 dark:text-cyan-400">
                                  {prov.cuota}%
                                </span>
                              </div>
                              <div className="mt-0.5 flex justify-between text-[11px] text-muted-foreground">
                                <span>RUT: {formatRUT(prov.proveedor_rut)}</span>
                                <span className="font-mono text-emerald-600 dark:text-emerald-400">
                                  {formatCLP(prov.monto_adjudicado)}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Buyers */}
                  <Card className="border border-border/80 bg-card p-4 shadow-sm">
                    <CardHeader className="p-0 pb-3">
                      <CardTitle className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        <Landmark className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span>Organismos Más Demandantes</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      {selectedCategoria.principales_organismos.length === 0 ? (
                        <p className="py-4 text-center text-xs text-muted-foreground">
                          Sin compradores registrados todavía.
                        </p>
                      ) : (
                        <div className="divide-y divide-border/60">
                          {selectedCategoria.principales_organismos.map((org) => (
                            <div key={org.organismo_id} className="py-2 text-xs">
                              <div className="flex justify-between font-semibold text-foreground">
                                <span className="truncate pr-2">
                                  {org.organismo_nombre ?? 'Sin nombre'}
                                </span>
                                <span className="text-muted-foreground">
                                  {org.total_licitaciones} procesos
                                </span>
                              </div>
                              <div className="mt-0.5 text-right font-mono text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                                {formatCLP(org.monto_comprado)}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Modal Footer */}
                <div className="mt-6 flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={closeCategoriaDetail}
                    className="rounded-md border-border/80 bg-background text-xs font-medium text-foreground shadow-sm hover:bg-muted"
                  >
                    Cerrar
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};
