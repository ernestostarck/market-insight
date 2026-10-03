import React from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, FolderTree, Eye } from 'lucide-react';
import { formatCLP } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import type { Categoria } from '@/types';
import type { CategoriaSortField, SortDirection } from '../hooks/useCategorias';

interface CategoriasTableProps {
  items: Categoria[];
  isLoading?: boolean;
  sortField?: CategoriaSortField;
  sortDirection?: SortDirection;
  onSort?: (field: CategoriaSortField) => void;
  onSelectCategoria?: (cat: Categoria) => void;
}

export const CategoriasTable: React.FC<CategoriasTableProps> = ({
  items,
  isLoading,
  sortField,
  sortDirection,
  onSort,
  onSelectCategoria,
}) => {
  const renderSortIcon = (field: CategoriaSortField) => {
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
              <th className="px-4 py-3.5">Código</th>
              <th className="px-4 py-3.5">Rubro</th>
              <th className="px-4 py-3.5 text-center">Licitaciones</th>
              <th className="px-4 py-3.5 text-right">Monto Adjudicado</th>
              <th className="px-4 py-3.5 text-center">Proveedores</th>
              <th className="px-4 py-3.5 text-center">Compradores</th>
              <th className="px-4 py-3.5 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {Array.from({ length: 6 }).map((_, idx) => (
              <tr key={idx} className="animate-pulse">
                <td className="px-4 py-4">
                  <div className="h-4 w-20 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="h-4 w-48 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="mx-auto h-4 w-12 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="ml-auto h-4 w-24 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="mx-auto h-4 w-10 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="mx-auto h-4 w-10 rounded bg-muted" />
                </td>
                <td className="px-4 py-4">
                  <div className="ml-auto h-8 w-20 rounded bg-muted" />
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
        <FolderTree className="mb-3 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-base font-semibold text-foreground">No se encontraron rubros</h3>
        <p className="mt-1 max-w-md text-xs text-muted-foreground">
          Los rubros se registran cuando una licitación de ChileCompra trae su propia
          clasificación (CodigoCategoria/Categoria). Prueba ajustando el término de búsqueda.
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
                <span>Código</span>
                {renderSortIcon('codigo')}
              </button>
            </th>
            <th className="px-4 py-3.5">
              <button
                onClick={() => onSort?.('nombre')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Rubro</span>
                {renderSortIcon('nombre')}
              </button>
            </th>
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
                onClick={() => onSort?.('monto_total')}
                className="group inline-flex items-center justify-end hover:text-foreground"
              >
                <span>Monto Adjudicado</span>
                {renderSortIcon('monto_total')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-center">
              <button
                onClick={() => onSort?.('total_proveedores')}
                className="group inline-flex items-center hover:text-foreground"
              >
                <span>Proveedores</span>
                {renderSortIcon('total_proveedores')}
              </button>
            </th>
            <th className="px-4 py-3.5 text-center">Compradores</th>
            <th className="px-4 py-3.5 text-right">Acción</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60 bg-card">
          {items.map((cat) => (
            <tr key={cat.id} className="group transition-colors hover:bg-muted/40">
              {/* Código */}
              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs font-bold text-foreground">
                {cat.codigo ?? '—'}
              </td>

              {/* Nombre */}
              <td className="max-w-md py-3.5 pr-4">
                <button
                  onClick={() => onSelectCategoria?.(cat)}
                  className="block text-left font-medium text-foreground transition-colors hover:text-primary"
                >
                  {cat.clase ?? cat.nombre ?? 'Sin nombre'}
                </button>
                {(cat.segmento || cat.familia) && (
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {[cat.segmento, cat.familia].filter(Boolean).join(' / ')}
                  </p>
                )}
              </td>

              {/* Total licitaciones */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs font-bold text-foreground">
                {cat.total_licitaciones.toLocaleString('es-CL')}
              </td>

              {/* Monto Total */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                {formatCLP(cat.monto_total)}
              </td>

              {/* Proveedores */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs font-medium text-foreground">
                {cat.total_proveedores}
              </td>

              {/* Organismos */}
              <td className="whitespace-nowrap px-4 py-3.5 text-center text-xs font-medium text-foreground">
                {cat.total_organismos}
              </td>

              {/* Acción */}
              <td className="whitespace-nowrap px-4 py-3.5 text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onSelectCategoria?.(cat)}
                  className="h-8 gap-1 text-xs text-primary hover:bg-primary/10 rounded-md"
                  title="Ver detalle y actores líderes"
                >
                  <Eye className="h-3 w-3" />
                  <span>Detalle</span>
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
