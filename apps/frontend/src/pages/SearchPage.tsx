import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Sparkles,
  Filter,
  ChevronLeft,
  ChevronRight,
  Inbox,
  HelpCircle,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useSearch, SearchResultCard } from '@/features/search';
import type { SearchEntity } from '@/types';

export const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const {
    query,
    setQuery,
    selectedEntities,
    toggleEntity,
    results,
    totalResults,
    page,
    setPage,
    totalPages,
    isLoading,
    isFetching,
    conceptSuggestions,
  } = useSearch(searchParams.get('q') ?? '');

  // The header's global search navigates here with ?q=…; follow later searches too.
  const urlQuery = searchParams.get('q');
  useEffect(() => {
    if (urlQuery !== null) setQuery(urlQuery);
  }, [urlQuery, setQuery]);

  const entityOptions: { id: SearchEntity; label: string }[] = [
    { id: 'licitacion', label: 'Licitaciones Públicas' },
    { id: 'proveedor', label: 'Proveedores' },
    { id: 'organismo', label: 'Organismos Compradores' },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Search Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 text-center shadow-sm">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Búsqueda Vectorial + Similitud Léxica</span>
        </div>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-4xl">
          Buscador Semántico e Híbrido
        </h1>
        <p className="mx-auto mt-1 max-w-2xl text-sm text-muted-foreground">
          Encuentra licitaciones, proveedores del estado y organismos compradores mediante lenguaje
          natural, conceptos técnicos y códigos oficiales.
        </p>
      </div>

      {/* Main Search Bar & Quick Concepts */}
      <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Escribe lo que buscas (ej: 'camas clínicas eléctricas hospitalarias', 'RUT 76.432.189-5', 'CENABAST')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-12 rounded-md border-border bg-background pl-12 pr-4 text-base text-foreground shadow-sm placeholder:text-muted-foreground focus:ring-primary"
          />
        </div>

        {/* Concept suggestions */}
        <div className="mt-3 flex flex-wrap items-center gap-1.5 pt-1">
          <span className="mr-1 flex items-center gap-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            Sugerencias rápidas:
          </span>
          {conceptSuggestions.map((concept) => (
            <button
              key={concept}
              onClick={() => setQuery(concept)}
              className="rounded-md border border-border/80 bg-muted/40 px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:border-primary/50 hover:bg-muted"
            >
              {concept}
            </button>
          ))}
        </div>

        {/* Entity Filter Checkboxes */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/80 pt-4 text-xs">
          <div className="flex items-center gap-2 font-medium text-muted-foreground">
            <Filter className="h-3.5 w-3.5 text-primary" />
            <span>Filtrar por tipo de entidad:</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {entityOptions.map((opt) => {
              const active = selectedEntities.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  onClick={() => toggleEntity(opt.id)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                    active
                      ? 'border-primary/40 bg-primary/10 font-semibold text-primary shadow-sm'
                      : 'border-border/80 bg-background text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Hybrid Scoring Info Banner */}
      <div className="flex items-center justify-between rounded-lg border border-border/80 bg-muted/30 px-4 py-2.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-primary" />
          <span>
            El score combina <strong>45% Keyword Match</strong> (coincidencia de términos) +{' '}
            <strong>55% Similitud Semántica</strong> (embeddings NLP).
          </span>
        </div>
        {isFetching && (
          <span className="flex items-center gap-1.5 font-medium text-primary">
            <span className="h-1.5 w-1.5 animate-ping rounded-full bg-primary" />
            Buscando...
          </span>
        )}
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Se encontraron <strong className="font-semibold text-foreground">{totalResults}</strong>{' '}
          resultados
          {query ? ` para "${query}"` : ' destacados'}
        </span>
        <span>
          Página {page} de {totalPages}
        </span>
      </div>

      {/* Results Feed */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <div
              key={idx}
              className="h-28 animate-pulse rounded-xl border border-border/80 bg-muted/30"
            />
          ))
        ) : results.length === 0 ? (
          <Card className="rounded-xl border border-border/80 bg-card p-12 text-center shadow-sm">
            <Inbox className="mx-auto mb-3 h-12 w-12 text-muted-foreground/60" />
            <h3 className="text-base font-semibold text-foreground">
              No se encontraron coincidencias
            </h3>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              No hubo resultados para los términos ingresados. Prueba ampliando la búsqueda o
              seleccionando más tipos de entidades.
            </p>
          </Card>
        ) : (
          results.map((res) => (
            <SearchResultCard key={`${res.entity_type}-${res.id}`} result={res} />
          ))
        )}
      </div>

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-border/80 pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="rounded-md border-border/80 bg-background text-xs font-medium text-foreground shadow-sm hover:bg-muted"
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            <span>Anterior</span>
          </Button>

          <span className="text-xs text-muted-foreground">
            Página <strong className="font-semibold text-foreground">{page}</strong> de {totalPages}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="rounded-md border-border/80 bg-background text-xs font-medium text-foreground shadow-sm hover:bg-muted"
          >
            <span>Siguiente</span>
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
};
