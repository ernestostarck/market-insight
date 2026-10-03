import React from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { LicitacionFilters } from '@/types';

interface LicitacionesFilterBarProps {
  filters: LicitacionFilters;
  onFilterChange: (newFilters: Partial<LicitacionFilters>) => void;
  onResetFilters: () => void;
}

export const LicitacionesFilterBar: React.FC<LicitacionesFilterBarProps> = ({
  filters,
  onFilterChange,
  onResetFilters,
}) => {
  const hasActiveFilters = Boolean(
    filters.q || (filters.estado && filters.estado !== 'all') || filters.solo_relevantes,
  );

  return (
    <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Buscar por código (ej: 1057416-24-LE26), nombre de licitación u organismo..."
            value={filters.q || ''}
            onChange={(e) => onFilterChange({ q: e.target.value })}
            className="h-10 rounded-md border-border bg-background pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary shadow-2xs"
          />
        </div>

        {/* Filter selects */}
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-1 lg:w-auto">
          {/* Estado */}
          <select
            value={filters.estado || 'all'}
            onChange={(e) => onFilterChange({ estado: e.target.value })}
            className="h-10 rounded-md border border-border bg-background px-3 text-xs font-semibold text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary shadow-2xs cursor-pointer"
          >
            <option value="all">Estado: Todos</option>
            <option value="publicada">Publicada (Vigente)</option>
            <option value="adjudicada">Adjudicada</option>
            <option value="cerrada">Cerrada</option>
            <option value="desierta">Desierta</option>
          </select>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onResetFilters}
              className="h-10 gap-1 text-xs font-semibold text-destructive hover:bg-destructive/10 rounded-md"
            >
              <X className="h-3.5 w-3.5" />
              <span>Limpiar</span>
            </Button>
          )}

          <div className="hidden items-center gap-1.5 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs font-semibold text-muted-foreground lg:flex">
            <Filter className="h-3.5 w-3.5 text-primary" />
            <span>MercadoPúblico</span>
          </div>
        </div>
      </div>
    </div>
  );
};
