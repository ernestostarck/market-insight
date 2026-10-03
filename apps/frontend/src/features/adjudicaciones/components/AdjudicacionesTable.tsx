import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpDown, ArrowUp, ArrowDown, Award, ExternalLink, TrendingDown } from 'lucide-react';
import { formatCLP, formatDate, formatRUT } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import type { Adjudicacion } from '@/types';
import type { AdjudicacionSortField, SortDirection } from '../hooks/useAdjudicaciones';

interface AdjudicacionesTableProps {
  items: Adjudicacion[];
  isLoading?: boolean;
  sortField?: AdjudicacionSortField;
  sortDirection?: SortDirection;
  onSort?: (field: AdjudicacionSortField) => void;
}

export const AdjudicacionesTable: React.FC<AdjudicacionesTableProps> = ({
  items,
  isLoading,
  sortField,
  sortDirection,
  onSort,
}) => {
  const renderSortIcon = (field: AdjudicacionSortField) => {
    if (!onSort) return null;
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 h-3 w-3 text-muted-foreground group-hover:text-foreground" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="ml-1 h-3.5 w-3.5 text-primary" />
    ) : (
      <ArrowDown className="ml-1 h-3.5 w-3.5 text-primary" />
    );
  };

  if (isLoading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-foreground">
          <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-3.5">Licitación / Proceso</th>
              <th className="px-4 py-3.5">Proveedor Adjudicado</th>
              <th className="px-4 py-3.5">Organismo</th>
              <th className="px-4 py-3.5 text-right">Monto Adjudicado</th>
              <th className="px-4 py-3.5 text-center">Desviación Ref.</th>
              <th className="px-4 py-3.5 text-center">Fecha</th>
              <th className="px-4 py-3.5 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {Array.from({ length: 6 }).map((_, idx) => (
              <tr key={idx} className="animate-pulse">
                <td className="px-4 py-4">
                  <div className="h-4 w-48 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-36 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-32 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="ml-auto h-4 w-24 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="mx-auto h-4 w-16 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="mx-auto h-4 w-20 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="ml-auto h-8 w-16 rounded bg-muted" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <Award className="mb-3 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-base font-semibold text-foreground">No se encontraron adjudicaciones</h3>
        <p className="mt-1 max-w-md text-xs text-muted-foreground">
          Prueba ajustando los filtros de búsqueda por proveedor, organismo o rango de monto.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-foreground">
        <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="px-4 py-3.5">Licitación / Proceso</th>
            <th className="px-4 py-3.5">
              <button
                onClick={() => onSort?.('proveedor_razon_social')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Proveedor Adjudicado</span>
                {renderSortIcon('proveedor_razon_social')}
              </button>
            </th>
            <th className="px-4 py-3.5">
              <button
                onClick={() => onSort?.('organismo_nombre')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Organismo Comprador</span>
                {renderSortIcon('organismo_nombre')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-right">
              <button
                onClick={() => onSort?.('monto_adjudicado')}
                className="group inline-flex items-center justify-end hover:text-foreground"
              >
                <span>Monto Adjudicado (CLP)</span>
                {renderSortIcon('monto_adjudicado')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-center">Margen vs Ref.</th>
            <th className="px-4 py-3.5 text-center">
              <button
                onClick={() => onSort?.('fecha_adjudicacion')}
                className="group inline-flex items-center justify-center hover:text-foreground"
              >
                <span>Fecha Adjudicación</span>
                {renderSortIcon('fecha_adjudicacion')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-right">Acción</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-card">
          {items.map((a) => (
            <tr key={a.id} className="group transition-colors hover:bg-muted/40">
              {/* Licitación */}
              <td className="max-w-xs px-4 py-3.5">
                <Link
                  to={`/licitaciones/${a.licitacion_id}`}
                  className="block truncate font-semibold text-foreground transition-colors hover:text-primary"
                >
                  {a.licitacion_nombre}
                </Link>
                <span className="font-mono text-xs text-muted-foreground">{a.licitacion_codigo}</span>
              </td>

              {/* Proveedor */}
              <td className="max-w-xs px-4 py-3.5">
                <Link
                  to={`/proveedores/${a.proveedor_id}`}
                  className="block truncate font-medium text-foreground hover:text-primary"
                >
                  {a.proveedor_razon_social}
                </Link>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {formatRUT(a.proveedor_rut)}
                </span>
              </td>

              {/* Organismo */}
              <td className="max-w-xs px-4 py-3.5 text-xs text-foreground">
                <Link
                  to={`/organismos/${a.organismo_id}`}
                  className="block truncate hover:text-primary"
                >
                  {a.organismo_nombre}
                </Link>
              </td>

              {/* Monto Adjudicado */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                {formatCLP(a.monto_adjudicado)}
              </td>

              {/* Desviación */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center">
                {a.desviacion_precio_referencial !== undefined &&
                a.desviacion_precio_referencial !== null ? (
                  <span
                    className={`inline-flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                      a.desviacion_precio_referencial <= 0
                        ? 'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                        : 'border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                    }`}
                  >
                    <TrendingDown className="h-3 w-3" />
                    {a.desviacion_precio_referencial}%
                  </span>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </td>

              {/* Fecha */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs text-muted-foreground">
                {formatDate(a.fecha_adjudicacion)}
              </td>

              {/* Acción */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right">
                <Button
                  asChild
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1 text-xs text-primary hover:bg-primary/10 rounded-md"
                >
                  <Link to={`/licitaciones/${a.licitacion_id}`}>
                    <span>Ficha</span>
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
