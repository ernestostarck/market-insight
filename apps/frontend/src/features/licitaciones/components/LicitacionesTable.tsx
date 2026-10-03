import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  Building2,
  Calendar,
  Inbox,
} from 'lucide-react';
import { formatCLP, formatDate } from '@/lib/formatters';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Licitacion } from '@/types';
import type { ColumnDefinition } from './ColumnVisibilitySelector';

export const DEFAULT_COLUMNS: ColumnDefinition[] = [
  { id: 'codigo', label: 'Código', visible: true, required: true },
  { id: 'nombre', label: 'Licitación / Nombre', visible: true, required: true },
  { id: 'organismo', label: 'Organismo Comprador', visible: true },
  { id: 'categoria', label: 'Categoría / Rubro', visible: true },
  { id: 'monto', label: 'Monto Estimado', visible: true },
  { id: 'estado', label: 'Estado', visible: true },
  { id: 'fechas', label: 'Fechas Clave', visible: true },
  { id: 'acciones', label: 'Acciones', visible: true, required: true },
];

interface LicitacionesTableProps {
  items: Licitacion[];
  isLoading?: boolean;
  visibleColumns?: ColumnDefinition[];
}

type SortField = 'codigo' | 'nombre' | 'monto' | 'fecha_publicacion' | 'fecha_cierre' | 'estado';
type SortDirection = 'asc' | 'desc';

export const LicitacionesTable: React.FC<LicitacionesTableProps> = ({
  items,
  isLoading,
  visibleColumns = DEFAULT_COLUMNS,
}) => {
  const [sortField, setSortField] = useState<SortField>('fecha_publicacion');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const visibleColumnMap = useMemo(() => {
    return new Set(visibleColumns.filter((c) => c.visible).map((c) => c.id));
  }, [visibleColumns]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortField) {
        case 'codigo':
          aVal = a.codigo || '';
          bVal = b.codigo || '';
          break;
        case 'nombre':
          aVal = a.nombre || '';
          bVal = b.nombre || '';
          break;
        case 'monto':
          aVal = a.monto_estimado || 0;
          bVal = b.monto_estimado || 0;
          break;
        case 'fecha_publicacion':
          aVal = a.fecha_publicacion || '';
          bVal = b.fecha_publicacion || '';
          break;
        case 'fecha_cierre':
          aVal = a.fecha_cierre || '';
          bVal = b.fecha_cierre || '';
          break;
        case 'estado':
          aVal = a.estado || '';
          bVal = b.estado || '';
          break;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [items, sortField, sortDirection]);

  const getStatusBadge = (estado?: string | null) => {
    const s = (estado || '').toLowerCase();
    if (s.includes('public') || s.includes('vigente')) {
      return (
        <Badge
          variant="outline"
          className="border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 font-semibold text-xs"
        >
          Publicada
        </Badge>
      );
    }
    if (s.includes('adjudic')) {
      return (
        <Badge
          variant="outline"
          className="border-blue-500/30 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 font-semibold text-xs"
        >
          Adjudicada
        </Badge>
      );
    }
    if (s.includes('desiert') || s.includes('cancel') || s.includes('revoc')) {
      return (
        <Badge
          variant="outline"
          className="border-rose-500/30 bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 font-semibold text-xs"
        >
          {estado || 'Desierta'}
        </Badge>
      );
    }
    if (s.includes('cerrad')) {
      return (
        <Badge
          variant="outline"
          className="border-border bg-muted text-muted-foreground font-semibold text-xs"
        >
          Cerrada
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="border-border bg-muted/60 text-muted-foreground font-medium text-xs">
        {estado || 'Sin estado'}
      </Badge>
    );
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1.5 h-3 w-3 text-muted-foreground group-hover:text-foreground" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="ml-1.5 h-3.5 w-3.5 text-primary" />
    ) : (
      <ArrowDown className="ml-1.5 h-3.5 w-3.5 text-primary" />
    );
  };

  if (isLoading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-foreground">
          <thead className="border-b border-border bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-3.5">Código</th>
              <th className="px-4 py-3.5">Licitación</th>
              <th className="px-4 py-3.5">Organismo</th>
              <th className="px-4 py-3.5">Monto Estimado</th>
              <th className="px-4 py-3.5">Estado</th>
              <th className="px-4 py-3.5">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 bg-card">
            {Array.from({ length: 6 }).map((_, idx) => (
              <tr key={idx} className="animate-pulse">
                <td className="px-4 py-4">
                  <div className="h-4 w-24 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-64 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-40 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-28 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-20 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-8 w-24 rounded bg-muted" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (sortedItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Inbox className="h-7 w-7" />
        </div>
        <h3 className="mt-4 text-base font-semibold text-foreground">
          No se encontraron licitaciones
        </h3>
        <p className="mt-1 max-w-md text-xs text-muted-foreground">
          Intenta ajustar los criterios de búsqueda, estado o filtros de categoría para encontrar
          procesos de compra pública.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-foreground">
        <thead className="border-b border-border bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          <tr>
            {visibleColumnMap.has('codigo') && (
              <th className="px-4 py-3.5">
                <button
                  onClick={() => handleSort('codigo')}
                  className="group inline-flex items-center hover:text-foreground font-bold"
                >
                  <span>Código</span>
                  {renderSortIcon('codigo')}
                </button>
              </th>
            )}

            {visibleColumnMap.has('nombre') && (
              <th className="px-4 py-3.5">
                <button
                  onClick={() => handleSort('nombre')}
                  className="group inline-flex items-center hover:text-foreground font-bold"
                >
                  <span>Licitación / Nombre</span>
                  {renderSortIcon('nombre')}
                </button>
              </th>
            )}

            {visibleColumnMap.has('organismo') && (
              <th className="px-4 py-3.5 font-bold">Organismo Comprador</th>
            )}

            {visibleColumnMap.has('categoria') && (
              <th className="px-4 py-3.5 font-bold">Categoría / Rubro</th>
            )}

            {visibleColumnMap.has('monto') && (
              <th className="px-4 py-3.5 text-right font-bold">
                <button
                  onClick={() => handleSort('monto')}
                  className="group inline-flex items-center justify-end hover:text-foreground font-bold"
                >
                  <span>Monto Estimado</span>
                  {renderSortIcon('monto')}
                </button>
              </th>
            )}

            {visibleColumnMap.has('estado') && (
              <th className="px-4 py-3.5 text-center font-bold">
                <button
                  onClick={() => handleSort('estado')}
                  className="group inline-flex items-center justify-center hover:text-foreground font-bold"
                >
                  <span>Estado</span>
                  {renderSortIcon('estado')}
                </button>
              </th>
            )}

            {visibleColumnMap.has('fechas') && (
              <th className="px-4 py-3.5 font-bold">
                <button
                  onClick={() => handleSort('fecha_cierre')}
                  className="group inline-flex items-center hover:text-foreground font-bold"
                >
                  <span>Cierre / Plazos</span>
                  {renderSortIcon('fecha_cierre')}
                </button>
              </th>
            )}

            {visibleColumnMap.has('acciones') && (
              <th className="px-4 py-3.5 text-right font-bold">Acciones</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-card">
          {sortedItems.map((item) => (
            <tr key={item.id} className="group transition-colors hover:bg-muted/40">
              {/* Código */}
              {visibleColumnMap.has('codigo') && (
                <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs font-bold text-primary">
                  <Link
                    to={`/licitaciones/${item.id}`}
                    className="flex items-center gap-1.5 hover:underline"
                  >
                    <span>{item.codigo}</span>
                  </Link>
                </td>
              )}

              {/* Nombre */}
              {visibleColumnMap.has('nombre') && (
                <td className="max-w-xs px-4 py-3.5 lg:max-w-md">
                  <Link
                    to={`/licitaciones/${item.id}`}
                    className="line-clamp-2 block font-semibold text-foreground transition-colors hover:text-primary"
                  >
                    {item.nombre}
                  </Link>
                  {item.descripcion && (
                    <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{item.descripcion}</p>
                  )}
                </td>
              )}

              {/* Organismo */}
              {visibleColumnMap.has('organismo') && (
                <td className="max-w-[200px] px-4 py-3.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                    <Building2 className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                    <span className="truncate">
                      {item.organismo?.nombre || 'Organismo Público'}
                    </span>
                  </div>
                  {item.region && (
                    <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">
                      {item.region}
                    </span>
                  )}
                </td>
              )}

              {/* Categoría */}
              {visibleColumnMap.has('categoria') && (
                <td className="whitespace-nowrap px-4 py-3.5 text-xs">
                  <span className="inline-block rounded-md border border-border bg-muted/40 px-2 py-1 text-[11px] font-medium text-muted-foreground">
                    {item.categoria || 'Equipamiento Médico'}
                  </span>
                </td>
              )}

              {/* Monto */}
              {visibleColumnMap.has('monto') && (
                <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                  {item.monto_estimado ? formatCLP(item.monto_estimado) : 'No informado'}
                </td>
              )}

              {/* Estado */}
              {visibleColumnMap.has('estado') && (
                <td className="whitespace-nowrap px-4 py-3.5 text-center">
                  {getStatusBadge(item.estado)}
                </td>
              )}

              {/* Fechas */}
              {visibleColumnMap.has('fechas') && (
                <td className="whitespace-nowrap px-4 py-3.5 text-xs">
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Calendar className="h-3 w-3 text-muted-foreground" />
                    <span>
                      Pub: {item.fecha_publicacion ? formatDate(item.fecha_publicacion) : '—'}
                    </span>
                  </div>
                  <div className="mt-0.5 text-[11px] font-semibold text-amber-600 dark:text-amber-400">
                    Cierre: {item.fecha_cierre ? formatDate(item.fecha_cierre) : '—'}
                  </div>
                </td>
              )}

              {/* Acciones */}
              {visibleColumnMap.has('acciones') && (
                <td className="whitespace-nowrap px-4 py-3.5 text-right">
                  <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1.5 text-xs font-semibold text-primary hover:bg-primary/10 rounded-md"
                  >
                    <Link to={`/licitaciones/${item.id}`}>
                      <span>Ver ficha</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
