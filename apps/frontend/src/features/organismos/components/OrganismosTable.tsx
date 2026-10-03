import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpDown, ArrowUp, ArrowDown, Landmark, ExternalLink, Clock } from 'lucide-react';
import { formatCLP, formatRUT } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import type { Organismo } from '@/types';
import type { OrganismoSortField, SortDirection } from '../hooks/useOrganismos';

interface OrganismosTableProps {
  items: Organismo[];
  isLoading?: boolean;
  sortField?: OrganismoSortField;
  sortDirection?: SortDirection;
  onSort?: (field: OrganismoSortField) => void;
}

export const OrganismosTable: React.FC<OrganismosTableProps> = ({
  items,
  isLoading,
  sortField,
  sortDirection,
  onSort,
}) => {
  const renderSortIcon = (field: OrganismoSortField) => {
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

  const getPaymentTermBadge = (days?: number) => {
    if (days == null) return <span className="text-xs text-muted-foreground">—</span>;
    let colorClass = 'border-border bg-muted text-muted-foreground';
    const label = `${days} días`;

    if (days <= 30) {
      colorClass = 'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300';
    } else if (days <= 45) {
      colorClass = 'border-blue-500/30 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300';
    } else {
      colorClass = 'border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300';
    }

    return (
      <div className="flex items-center gap-1.5">
        <Clock className="h-3 w-3 text-muted-foreground" />
        <span
          className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${colorClass}`}
        >
          {label}
        </span>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-foreground">
          <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-3.5">Organismo / Institución</th>
              <th className="px-4 py-3.5">RUT</th>
              <th className="px-4 py-3.5">Sector & Región</th>
              <th className="px-4 py-3.5 text-center">Licitaciones</th>
              <th className="px-4 py-3.5 text-right">Presupuesto Comprado</th>
              <th className="px-4 py-3.5">Plazo Pago Prom.</th>
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
        <Landmark className="mb-3 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-base font-semibold text-foreground">No se encontraron organismos</h3>
        <p className="mt-1 max-w-md text-xs text-muted-foreground">
          Prueba ajustando la búsqueda por nombre o código.
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
                onClick={() => onSort?.('nombre')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Organismo Comprador</span>
                {renderSortIcon('nombre')}
              </button>
            </th>
            <th className="px-4 py-3.5">RUT</th>
            <th className="px-4 py-3.5">Sector & Región</th>
            <th className="px-4 py-3.5 text-center">
              <button
                onClick={() => onSort?.('total_licitaciones')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Licitaciones</span>
                {renderSortIcon('total_licitaciones')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-right">
              <button
                onClick={() => onSort?.('monto_total_comprado')}
                className="group inline-flex items-center justify-end hover:text-foreground"
              >
                <span>Total Comprado (CLP)</span>
                {renderSortIcon('monto_total_comprado')}
              </button>
            </th>
            <th className="px-4 py-3.5">Pago Promedio</th>
            <th className="px-4 py-3.5 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-card">
          {items.map((o) => (
            <tr key={o.id} className="group transition-colors hover:bg-muted/40">
              {/* Organismo */}
              <td className="max-w-xs px-4 py-3.5">
                <Link
                  to={`/organismos/${o.id}`}
                  className="block truncate font-semibold text-foreground transition-colors hover:text-primary"
                >
                  {o.nombre || 'Organismo Sin Nombre'}
                </Link>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Cód: {o.codigo}</span>
                  {o.categoria_principal && (
                    <>
                      <span>•</span>
                      <span className="truncate text-muted-foreground">{o.categoria_principal}</span>
                    </>
                  )}
                </div>
              </td>

              {/* RUT */}
              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs font-medium text-foreground">
                {formatRUT(o.rut)}
              </td>

              {/* Sector & Región */}
              <td className="px-4 py-3.5 text-xs">
                <span className="inline-block rounded border border-border/80 bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {o.sector || '—'}
                </span>
                {o.region && (
                  <span className="mt-0.5 block text-[11px] text-muted-foreground">{o.region}</span>
                )}
              </td>

              {/* Licitaciones */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs">
                <span className="font-bold text-foreground">{o.total_licitaciones || 0}</span>
                {o.licitaciones_activas !== undefined && (
                  <span className="ml-1.5 inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                    {o.licitaciones_activas} activas
                  </span>
                )}
              </td>

              {/* Monto Total */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                {o.monto_total_comprado ? formatCLP(o.monto_total_comprado) : '$0 CLP'}
              </td>

              {/* Pago Promedio */}
              <td className="whitespace-nowrap px-4 py-3.5">
                {getPaymentTermBadge(o.dias_pago_promedio)}
              </td>

              {/* Acciones */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right">
                <Button
                  asChild
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1 text-xs text-primary hover:bg-primary/10 rounded-md"
                >
                  <Link to={`/organismos/${o.id}`}>
                    <span>Perfil</span>
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
