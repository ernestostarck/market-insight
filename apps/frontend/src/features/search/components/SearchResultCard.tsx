import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Building2, Landmark, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SearchScoreBadge } from './SearchScoreBadge';
import type { SearchResult } from '@/types';

interface SearchResultCardProps {
  result: SearchResult;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({ result }) => {
  const getEntityConfig = () => {
    switch (result.entity_type) {
      case 'licitacion':
        return {
          label: 'Licitación Pública',
          icon: FileText,
          href: `/licitaciones/${result.id}`,
          badgeClass: 'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
        };
      case 'proveedor':
        return {
          label: 'Proveedor del Estado',
          icon: Building2,
          href: `/proveedores/${result.id}`,
          badgeClass: 'border-blue-500/30 bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
        };
      case 'organismo':
        return {
          label: 'Organismo Comprador',
          icon: Landmark,
          href: `/organismos/${result.id}`,
          badgeClass: 'border-purple-500/30 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300',
        };
    }
  };

  const config = getEntityConfig();
  const IconComponent = config.icon;

  return (
    <div className="group rounded-xl border border-border/80 bg-card p-4 transition-all hover:border-primary/40 hover:shadow-md">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div className="flex-1 space-y-2">
          {/* Entity Tag and Code */}
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={`gap-1 px-2 py-0.5 text-[11px] ${config.badgeClass}`}
            >
              <IconComponent className="h-3 w-3" />
              <span>{config.label}</span>
            </Badge>

            {result.code && (
              <span className="font-mono text-xs font-semibold text-foreground">{result.code}</span>
            )}
          </div>

          {/* Title */}
          <Link
            to={config.href}
            className="block text-base font-semibold text-foreground transition-colors group-hover:text-primary"
          >
            {result.title}
          </Link>

          {/* Subtitle / Metadata details */}
          {result.subtitle && (
            <p className="line-clamp-2 text-xs text-muted-foreground">{result.subtitle}</p>
          )}

          {/* Search Score breakdown (only when the API actually computed one) */}
          {result.score !== undefined && (
            <div className="pt-1">
              <SearchScoreBadge
                score={result.score}
                semanticScore={result.semantic_score}
                keywordScore={result.keyword_score}
              />
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="sm:self-center">
          <Button
            asChild
            variant="outline"
            size="sm"
            className="h-9 gap-1.5 border-border/80 bg-background text-foreground hover:bg-primary hover:text-white hover:border-primary text-xs font-medium rounded-md shadow-sm transition-all"
          >
            <Link to={config.href}>
              <span>Ver Ficha</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
};
