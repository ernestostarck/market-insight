import React, { useState } from 'react';
import { RefreshCw, FileSpreadsheet, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  useLicitaciones,
  LicitacionesFilterBar,
  LicitacionesTable,
  CursorPagination,
  ColumnVisibilitySelector,
  DEFAULT_COLUMNS,
  type ColumnDefinition,
} from '@/features/licitaciones';

export const LicitacionesPage: React.FC = () => {
  const [visibleColumns, setVisibleColumns] = useState<ColumnDefinition[]>(DEFAULT_COLUMNS);

  const {
    data,
    isLoading,
    isFetching,
    refetch,
    filters,
    setFilters,
    resetFilters,
    limit,
    setLimit,
    pageNumber,
    goToNextPage,
    goToPreviousPage,
    hasNextPage,
    hasPreviousPage,
  } = useLicitaciones({ defaultLimit: 10 });

  const handleToggleColumn = (columnId: string) => {
    setVisibleColumns((prev) =>
      prev.map((col) => (col.id === columnId ? { ...col, visible: !col.visible } : col)),
    );
  };

  const handleResetColumns = () => {
    setVisibleColumns(DEFAULT_COLUMNS);
  };

  const handleExportCsv = () => {
    if (!data || data.data.length === 0) return;
    const headers = [
      'Código',
      'Nombre',
      'Organismo',
      'Categoría',
      'Monto Estimado',
      'Estado',
      'Fecha Publicación',
    ];
    const rows = data.data.map((item) => [
      `"${item.codigo}"`,
      `"${item.nombre.replace(/"/g, '""')}"`,
      `"${item.organismo?.nombre || ''}"`,
      `"${item.categoria || ''}"`,
      item.monto_estimado || 0,
      `"${item.estado || ''}"`,
      `"${item.fecha_publicacion || ''}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute(
      'download',
      `licitaciones_export_${new Date().toISOString().slice(0, 10)}.csv`,
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Explorador de Licitaciones
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-500/20 bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-pulse" />
                ChileCompra
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Catálogo completo, búsqueda por criterios, monitoreo de bases técnicas y pertinencia IA
              en compras públicas.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Column selector */}
            <ColumnVisibilitySelector
              columns={visibleColumns}
              onToggleColumn={handleToggleColumn}
              onResetColumns={handleResetColumns}
            />

            {/* CSV Export */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCsv}
              className="flex items-center gap-2 border-border/80 bg-background text-foreground hover:bg-muted font-medium text-xs rounded-md shadow-sm transition-all"
              title="Exportar página actual a CSV"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Exportar</span>
            </Button>

            {/* Refetch button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-2 border-primary/30 text-primary hover:bg-primary hover:text-white font-medium text-xs rounded-md shadow-sm transition-all"
              title="Refrescar catálogo"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
              <span>Refrescar</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <LicitacionesFilterBar
        filters={filters}
        onFilterChange={setFilters}
        onResetFilters={resetFilters}
      />

      {/* Data Table Card */}
      <Card className="overflow-hidden border border-border/80 bg-card shadow-sm rounded-xl">
        <div className="flex items-center justify-between border-b border-border/80 px-5 py-3.5 bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="rounded-md bg-primary/10 p-1.5 text-primary">
              <Layers className="h-4 w-4" />
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-foreground">
              Licitaciones Registradas
            </span>
            {data && (
              <span className="rounded-full bg-muted border border-border/60 px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">
                {data.total} procesos
              </span>
            )}
          </div>
          {isFetching && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-primary">
              <span className="h-2 w-2 animate-ping rounded-full bg-primary" />
              Sincronizando...
            </span>
          )}
        </div>

        <LicitacionesTable
          items={data?.data || []}
          isLoading={isLoading}
          visibleColumns={visibleColumns}
        />

        <CursorPagination
          total={data?.total || 0}
          pageSize={limit}
          pageNumber={pageNumber}
          hasNext={hasNextPage}
          hasPrevious={hasPreviousPage}
          onNext={goToNextPage}
          onPrevious={goToPreviousPage}
          onPageSizeChange={setLimit}
          isLoading={isFetching}
        />
      </Card>
    </div>
  );
};
