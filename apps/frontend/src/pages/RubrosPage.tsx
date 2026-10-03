import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Boxes,
  Check,
  ChevronDown,
  Cpu,
  HardHat,
  HeartPulse,
  Briefcase,
  Package,
  RefreshCw,
  Shirt,
  Sparkles,
  Truck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useTaxonomia } from '@/features/taxonomia';
import { setSegmento, useSegmento, type Segmento } from '@/features/segmento';
import type { TaxonomiaCategoria } from '@/types';

const CATEGORY_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  technology: Cpu,
  health: HeartPulse,
  construction: HardHat,
  transport: Truck,
  'professional-services': Briefcase,
  'general-supplies': Package,
  apparel: Shirt,
};

function RubroCard({
  categoria,
  isExpanded,
  onToggle,
  activeCode,
  onSelect,
}: {
  categoria: TaxonomiaCategoria;
  isExpanded: boolean;
  onToggle: () => void;
  activeCode: string | null;
  onSelect: (segmento: Segmento) => void;
}) {
  const Icon = CATEGORY_ICON[categoria.code] ?? Boxes;
  const conceptCount = categoria.subcategories.reduce((n, s) => n + s.concepts.length, 0);
  const categoryCode = `cat:${categoria.code}`;
  const isCategoryActive = activeCode === categoryCode;
  const hasActiveConcept = categoria.subcategories.some((s) =>
    s.concepts.some((c) => activeCode === `concept:${c.code}`),
  );

  return (
    <Card
      className={cn(
        'overflow-hidden border border-border/80 bg-card',
        (isCategoryActive || hasActiveConcept) && 'border-primary/60 ring-1 ring-primary/40',
      )}
    >
      <div className="flex w-full items-center gap-3 p-4 transition-colors hover:bg-muted/40">
        <button
          type="button"
          onClick={onToggle}
          className="flex min-w-0 flex-1 items-center gap-3 text-left"
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20">
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">{categoria.name}</h3>
              {categoria.code === 'apparel' && (
                <span className="rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                  Nuevo
                </span>
              )}
            </div>
            <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
              {categoria.description}
            </p>
          </div>
          <div className="hidden shrink-0 text-right sm:block">
            <span className="text-[11px] font-medium text-muted-foreground">
              {categoria.subcategories.length} subrubros · {conceptCount} conceptos
            </span>
          </div>
        </button>
        <Button
          type="button"
          size="sm"
          variant={isCategoryActive ? 'default' : 'outline'}
          onClick={() => onSelect({ code: categoryCode, label: categoria.name })}
          className="h-8 shrink-0 gap-1.5 text-xs"
          aria-pressed={isCategoryActive}
        >
          {isCategoryActive && <Check className="h-3.5 w-3.5" />}
          {isCategoryActive ? 'Analizando' : 'Analizar rubro'}
        </Button>
        <button
          type="button"
          onClick={onToggle}
          aria-label={isExpanded ? 'Contraer rubro' : 'Expandir rubro'}
        >
          <ChevronDown
            className={cn(
              'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
              isExpanded && 'rotate-180',
            )}
          />
        </button>
      </div>

      {isExpanded && (
        <div className="divide-y divide-border/60 border-t border-border/80 bg-muted/10">
          {categoria.subcategories.map((sub) => (
            <div key={sub.code} className="p-4">
              <p className="text-xs font-semibold text-foreground">{sub.name}</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">{sub.description}</p>
              {sub.concepts.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {sub.concepts.map((concept) => {
                    const conceptCode = `concept:${concept.code}`;
                    const isActive = activeCode === conceptCode;
                    return (
                      <button
                        type="button"
                        key={concept.code}
                        title={`${concept.description} — clic para analizar el mercado de este concepto`}
                        onClick={() =>
                          onSelect({
                            code: conceptCode,
                            label: concept.name,
                            parentLabel: categoria.name,
                          })
                        }
                        aria-pressed={isActive}
                        className={cn(
                          'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors',
                          isActive
                            ? 'border-primary bg-primary text-primary-foreground'
                            : 'border-border/80 bg-background text-foreground hover:border-primary/50 hover:bg-primary/5',
                        )}
                      >
                        {isActive && <Check className="h-3 w-3" />}
                        {concept.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export const RubrosPage: React.FC = () => {
  const { version, categories, isLoading, isFetching, refetch, expanded, toggleCategory } =
    useTaxonomia();
  const segmento = useSegmento();
  const navigate = useNavigate();

  // Picking a rubro/concept rescopes the whole platform and opens its market view;
  // picking the active one again clears it.
  const handleSelect = (next: Segmento) => {
    if (segmento?.code === next.code) {
      setSegmento(null);
      return;
    }
    setSegmento(next);
    navigate('/mercado');
  };

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Rubros de Mercado
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200/90 bg-blue-50/90 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
                <Sparkles className="h-3 w-3" />
                Clasificación automática
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              Sectores y conceptos que la plataforma usa para clasificar licitaciones — incluye
              geriatría/accesibilidad y las líneas de negocio que se van sumando, como Vestuario.
              Elige un rubro o un concepto para enfocar toda la plataforma en ese mercado.
              {version && (
                <span className="ml-1 font-mono text-[11px] text-muted-foreground/70">
                  ({version})
                </span>
              )}
            </p>
          </div>

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

      {/* Rubros list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-[76px] animate-pulse rounded-xl border border-border/80 bg-muted/30"
            />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {categories.map((categoria) => (
            <RubroCard
              key={categoria.code}
              categoria={categoria}
              isExpanded={expanded.has(categoria.code)}
              onToggle={() => toggleCategory(categoria.code)}
              activeCode={segmento?.code ?? null}
              onSelect={handleSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};
