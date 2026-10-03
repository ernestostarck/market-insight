import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpDown, ArrowUp, ArrowDown, Building2, ExternalLink, Award } from 'lucide-react';
import { formatCLP, formatRUT } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import type { Proveedor } from '@/types';
import type { ProveedorSortField, SortDirection } from '../hooks/useProveedores';

interface ProveedoresTableProps {
  items: Proveedor[];
  isLoading?: boolean;
  sortField?: ProveedorSortField;
  sortDirection?: SortDirection;
  onSort?: (field: ProveedorSortField) => void;
  onCompare?: (proveedor: Proveedor) => void;
}

export const ProveedoresTable: React.FC<ProveedoresTableProps> = ({
  items,
  isLoading,
  sortField,
  sortDirection,
  onSort,
  onCompare,
}) => {
  const renderSortIcon = (field: ProveedorSortField) => {
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

  const getSuccessRateBadge = (rate: number | null | undefined) => {
    if (rate == null) return <span className="text-xs text-muted-foreground">—</span>;
    let colorClass = 'border-border bg-muted text-muted-foreground';
    if (rate >= 65) colorClass = 'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300';
    else if (rate >= 50) colorClass = 'border-blue-500/30 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300';
    else if (rate >= 35) colorClass = 'border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300';

    return (
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${colorClass}`}
        >
          {rate.toFixed(1)}%
        </span>
        <div className="hidden h-1.5 w-14 overflow-hidden rounded-full bg-muted md:block">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500"
            style={{ width: `${Math.min(100, rate)}%` }}
          />
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-foreground">
          <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-3.5">Proveedor</th>
              <th className="px-4 py-3.5">RUT</th>
              <th className="px-4 py-3.5">Categoría</th>
              <th className="px-4 py-3.5">Región</th>
              <th className="px-4 py-3.5 text-center">Licitaciones</th>
              <th className="px-4 py-3.5 text-right">Monto Adjudicado</th>
              <th className="px-4 py-3.5">Tasa Éxito</th>
              <th className="px-4 py-3.5 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {Array.from({ length: 6 }).map((_, idx) => (
              <tr key={idx} className="animate-pulse">
                <td className="px-4 py-4">
                  <div className="h-4 w-48 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-24 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-28 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-24 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="mx-auto h-4 w-16 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="ml-auto h-4 w-28 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-20 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="ml-auto h-8 w-24 rounded bg-muted" />
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
        <Building2 className="mb-3 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-base font-semibold text-foreground">No se encontraron proveedores</h3>
        <p className="mt-1 max-w-md text-xs text-muted-foreground">
          Prueba ajustando la búsqueda por nombre o RUT, o el rubro seleccionado.
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
                onClick={() => onSort?.('razon_social')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Proveedor / Razón Social</span>
                {renderSortIcon('razon_social')}
              </button>
            </th>
            <th className="px-4 py-3.5">RUT</th>
            <th className="px-4 py-3.5">Categoría</th>
            <th className="px-4 py-3.5">Región</th>
            <th className="px-4 py-3.5 text-center">
              <button
                onClick={() => onSort?.('total_adjudicaciones')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Adjudicadas</span>
                {renderSortIcon('total_adjudicaciones')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-right">
              <button
                onClick={() => onSort?.('monto_total_adjudicado')}
                className="group inline-flex items-center justify-end hover:text-foreground"
              >
                <span>Monto Total Adjudicado</span>
                {renderSortIcon('monto_total_adjudicado')}
              </button>
            </th>
            <th className="px-4 py-3.5">
              <button
                onClick={() => onSort?.('tasa_exito')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Tasa Éxito</span>
                {renderSortIcon('tasa_exito')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-card">
          {items.map((p) => (
            <tr key={p.id} className="group transition-colors hover:bg-muted/40">
              {/* Proveedor */}
              <td className="max-w-xs px-4 py-3.5">
                <Link
                  to={`/proveedores/${p.id}`}
                  className="block truncate font-semibold text-foreground transition-colors hover:text-primary"
                >
                  {p.razon_social}
                </Link>
                {p.nombre_fantasia && (
                  <span className="block truncate text-xs text-muted-foreground">
                    Alias: {p.nombre_fantasia}
                  </span>
                )}
              </td>

              {/* RUT */}
              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs font-medium text-foreground">
                {formatRUT(p.rut)}
              </td>

              {/* Categoría */}
              <td className="px-4 py-3.5 text-xs">
                <span className="inline-block rounded border border-border/80 bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {p.categoria_principal || 'Equipamiento Médico'}
                </span>
              </td>

              {/* Región */}
              <td className="whitespace-nowrap px-4 py-3.5 text-xs font-medium text-muted-foreground">
                {p.region || 'Metropolitana'}
              </td>

              {/* Adjudicaciones */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs">
                <span className="font-bold text-foreground">{p.total_adjudicaciones || 0}</span>
                <span className="ml-1 text-muted-foreground">
                  / {p.total_licitaciones_participadas || 0}
                </span>
              </td>

              {/* Monto Total */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                {p.monto_total_adjudicado ? formatCLP(p.monto_total_adjudicado) : '$0 CLP'}
              </td>

              {/* Tasa Éxito */}
              <td className="whitespace-nowrap px-4 py-3.5">{getSuccessRateBadge(p.tasa_exito)}</td>

              {/* Acciones */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right">
                <div className="flex items-center justify-end gap-1.5">
                  {onCompare && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onCompare(p)}
                      className="h-8 gap-1 text-xs text-cyan-600 hover:bg-cyan-50 dark:text-cyan-400 dark:hover:bg-cyan-950/30 rounded-md"
                      title="Agregar a comparador"
                    >
                      <Award className="h-3 w-3" />
                      <span className="hidden xl:inline">Comparar</span>
                    </Button>
                  )}

                  <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 text-xs text-primary hover:bg-primary/10 rounded-md"
                  >
                    <Link to={`/proveedores/${p.id}`}>
                      <span>Perfil</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
