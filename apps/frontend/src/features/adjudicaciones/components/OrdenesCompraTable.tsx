import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpDown, ArrowUp, ArrowDown, ShoppingBag, ExternalLink, FileText } from 'lucide-react';
import { formatCLP, formatDate, formatRUT } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import type { OrdenDeCompra } from '@/types';
import type { OrdenDeCompraSortField } from '../hooks/useOrdenesCompra';
import type { SortDirection } from '../hooks/useAdjudicaciones';

interface OrdenesCompraTableProps {
  items: OrdenDeCompra[];
  isLoading?: boolean;
  sortField?: OrdenDeCompraSortField;
  sortDirection?: SortDirection;
  onSort?: (field: OrdenDeCompraSortField) => void;
}

export const OrdenesCompraTable: React.FC<OrdenesCompraTableProps> = ({
  items,
  isLoading,
  sortField,
  sortDirection,
  onSort,
}) => {
  const renderSortIcon = (field: OrdenDeCompraSortField) => {
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

  const getStatusBadge = (status?: string | null) => {
    switch (status?.toLowerCase()) {
      case 'pagada':
        return (
          <span className="inline-flex rounded-full border border-emerald-500/30 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            Pagada
          </span>
        );
      case 'facturada':
        return (
          <span className="inline-flex rounded-full border border-cyan-500/30 bg-cyan-50 px-2 py-0.5 text-xs font-semibold text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-300">
            Facturada
          </span>
        );
      case 'recepcionada':
        return (
          <span className="inline-flex rounded-full border border-blue-500/30 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            Recepcionada
          </span>
        );
      case 'aceptada':
        return (
          <span className="inline-flex rounded-full border border-purple-500/30 bg-purple-50 px-2 py-0.5 text-xs font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
            Aceptada
          </span>
        );
      default:
        return (
          <span className="inline-flex rounded-full border border-border bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
            {status || 'Emitida'}
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-foreground">
          <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-3.5">Código OC</th>
              <th className="px-4 py-3.5">Licitación Origen</th>
              <th className="px-4 py-3.5">Proveedor</th>
              <th className="px-4 py-3.5">Organismo</th>
              <th className="px-4 py-3.5 text-right">Monto Total</th>
              <th className="px-4 py-3.5 text-center">Estado</th>
              <th className="px-4 py-3.5 text-center">Fecha</th>
              <th className="px-4 py-3.5 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {Array.from({ length: 6 }).map((_, idx) => (
              <tr key={idx} className="animate-pulse">
                <td className="px-4 py-4">
                  <div className="h-4 w-28 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-32 rounded bg-muted" />
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
        <ShoppingBag className="mb-3 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-base font-semibold text-foreground">No se encontraron órdenes de compra</h3>
        <p className="mt-1 max-w-md text-xs text-muted-foreground">
          Prueba ajustando los filtros de búsqueda por código, estado o proveedor.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-foreground">
        <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="px-4 py-3.5">
              <button
                onClick={() => onSort?.('codigo')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Código OC</span>
                {renderSortIcon('codigo')}
              </button>
            </th>
            <th className="px-4 py-3.5">Licitación Origen</th>
            <th className="px-4 py-3.5">Proveedor</th>
            <th className="px-4 py-3.5">Organismo</th>
            <th className="px-4 py-3.5 text-right">
              <button
                onClick={() => onSort?.('monto_total')}
                className="group inline-flex items-center justify-end hover:text-foreground"
              >
                <span>Monto Total (CLP)</span>
                {renderSortIcon('monto_total')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-center">Estado</th>
            <th className="px-4 py-3.5 text-center">
              <button
                onClick={() => onSort?.('fecha_creacion')}
                className="group inline-flex items-center justify-center hover:text-foreground"
              >
                <span>Fecha Emisión</span>
                {renderSortIcon('fecha_creacion')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-right">Acción</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-card">
          {items.map((oc) => (
            <tr key={oc.id} className="group transition-colors hover:bg-muted/40">
              {/* Código OC */}
              <td className="whitespace-nowrap px-4 py-3.5">
                <span className="font-mono text-xs font-bold text-foreground">{oc.codigo}</span>
                {oc.nombre && (
                  <p className="mt-0.5 max-w-xs truncate text-[11px] text-muted-foreground">{oc.nombre}</p>
                )}
              </td>

              {/* Licitación Origen */}
              <td className="max-w-xs px-4 py-3.5">
                {oc.licitacion_id ? (
                  <Link
                    to={`/licitaciones/${oc.licitacion_id}`}
                    className="inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline"
                  >
                    <FileText className="h-3 w-3" />
                    <span>{oc.licitacion_codigo || `LIC-${oc.licitacion_id}`}</span>
                  </Link>
                ) : (
                  <span className="font-mono text-xs text-muted-foreground">Sin licitación</span>
                )}
              </td>

              {/* Proveedor */}
              <td className="max-w-xs px-4 py-3.5 text-xs text-foreground">
                {oc.proveedor_id ? (
                  <Link to={`/proveedores/${oc.proveedor_id}`} className="hover:text-primary">
                    <span className="block truncate font-medium">
                      {oc.proveedor_nombre || 'Proveedor Registrado'}
                    </span>
                    {oc.proveedor_rut && (
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {formatRUT(oc.proveedor_rut)}
                      </span>
                    )}
                  </Link>
                ) : (
                  <span>{oc.proveedor_nombre || '-'}</span>
                )}
              </td>

              {/* Organismo */}
              <td className="max-w-xs px-4 py-3.5 text-xs text-foreground">
                {oc.organismo_id ? (
                  <Link to={`/organismos/${oc.organismo_id}`} className="hover:text-primary">
                    <span className="block truncate">{oc.organismo_nombre || 'Organismo Comprador'}</span>
                  </Link>
                ) : (
                  <span>{oc.organismo_nombre || '-'}</span>
                )}
              </td>

              {/* Monto Total */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                {oc.monto_total ? formatCLP(oc.monto_total) : '$0 CLP'}
              </td>

              {/* Estado */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center">{getStatusBadge(oc.estado)}</td>

              {/* Fecha */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs text-muted-foreground">
                {formatDate(oc.fecha_creacion || oc.fecha_envio)}
              </td>

              {/* Acción */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right">
                {oc.licitacion_id && (
                  <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 text-xs text-primary hover:bg-primary/10 rounded-md"
                  >
                    <Link to={`/licitaciones/${oc.licitacion_id}`}>
                      <span>Licitación</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
