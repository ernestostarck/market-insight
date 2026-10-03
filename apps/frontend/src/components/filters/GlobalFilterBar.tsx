import React, { useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, Filter, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useGlobalFilters } from '@/components/filters/useGlobalFilters';
import { cn } from '@/lib/utils';
import { setSegmento } from '@/features/segmento';

export function GlobalFilterBar({ className }: { className?: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { filters, activeFilterCount, setFilter, clearFilters, applyQuickPreset } =
    useGlobalFilters();

  return (
    <div
      className={cn(
        'space-y-3 rounded-xl border border-border/70 bg-card p-4 shadow-sm',
        className,
      )}
    >
      {/* Top Filter Bar: Header & Quick Presets */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-primary" />
          <span className="text-xs font-bold uppercase tracking-wider text-foreground">
            Filtros Globales
          </span>
          {activeFilterCount > 0 && (
            <Badge variant="default" className="h-5 px-1.5 text-[10px] font-bold">
              {activeFilterCount} activos
            </Badge>
          )}
        </div>

        {/* Quick Filter Presets */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 hidden text-[11px] text-muted-foreground sm:inline">Rápidos:</span>

          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2.5 text-xs"
            onClick={() => applyQuickPreset('last-30-days')}
          >
            Últimos 30 días
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2.5 text-xs"
            onClick={() => applyQuickPreset('year-2026')}
          >
            Año 2026
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1 px-2.5 text-xs"
            onClick={() => setSegmento({ code: 'cat:health', label: 'Salud' })}
            title="Enfoca toda la plataforma en el rubro Salud"
          >
            <Sparkles className="h-3 w-3 text-primary" />
            Rubro Salud
          </Button>


          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={clearFilters}
            >
              <X className="mr-1 h-3.5 w-3.5" />
              Limpiar
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => setIsExpanded((prev) => !prev)}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Expanded Multi-Criteria Filter Controls */}
      {isExpanded && (
        <div className="grid grid-cols-1 gap-3 border-t border-border/60 pt-3 sm:grid-cols-2 md:grid-cols-4">
          {/* Fecha Desde */}
          <div className="space-y-1">
            <label className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
              <Calendar className="h-3 w-3" /> Fecha Desde
            </label>
            <Input
              type="date"
              value={filters.startDate || ''}
              onChange={(e) => setFilter('startDate', e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          {/* Fecha Hasta */}
          <div className="space-y-1">
            <label className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
              <Calendar className="h-3 w-3" /> Fecha Hasta
            </label>
            <Input
              type="date"
              value={filters.endDate || ''}
              onChange={(e) => setFilter('endDate', e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          {/* Estado */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">
              Estado Licitación
            </label>
            <select
              value={filters.estado || ''}
              onChange={(e) => setFilter('estado', e.target.value)}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            >
              <option value="">Todos</option>
              <option value="publicada">Publicada</option>
              <option value="cerrada">Cerrada</option>
              <option value="adjudicada">Adjudicada</option>
              <option value="desierta">Desierta</option>
            </select>
          </div>

          {/* Organismo */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">
              Organismo / Licitación
            </label>
            <Input
              placeholder="Ej: Hospital San Juan"
              value={filters.organismo || ''}
              onChange={(e) => setFilter('organismo', e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          {/* Proveedor */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">
              Proveedor / RUT
            </label>
            <Input
              placeholder="Razón social o RUT"
              value={filters.proveedor || ''}
              onChange={(e) => setFilter('proveedor', e.target.value)}
              className="h-8 text-xs"
            />
          </div>
        </div>
      )}
    </div>
  );
}
