import React, { useState } from 'react';
import {
  ExternalLink,
  FileText,
  Building2,
  ShoppingCart,
  Database,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from 'lucide-react';
import type { AICitation, AISource } from '@/types/ai';

interface SourcesListProps {
  sources?: AISource[];
  citations?: AICitation[];
  className?: string;
}

export const SourcesList: React.FC<SourcesListProps> = ({
  sources = [],
  citations = [],
  className = '',
}) => {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Combine unique sources from either sources or citations
  const displayedSources = citations.length > 0
    ? citations.map((c) => ({
        id: c.source_id,
        source_type: c.source_type,
        title: c.title,
        snippet: c.snippet,
        score: c.relevance,
        url: c.url,
        target_route: c.target_route,
        is_verified: c.is_verified,
      }))
    : sources.map((s) => ({
        id: s.id,
        source_type: s.source_type,
        title: s.title,
        snippet: s.snippet,
        score: s.score,
        url: s.url,
        target_route: s.source_type === 'tender' ? `/licitaciones/${s.id}` : undefined,
        is_verified: true,
      }));

  if (displayedSources.length === 0) {
    return null;
  }

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyToClipboard = (id: string, text: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getSourceIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('tender') || t.includes('licitacion')) {
      return <FileText className="w-4 h-4 text-emerald-500" />;
    }
    if (t.includes('order') || t.includes('oc')) {
      return <ShoppingCart className="w-4 h-4 text-sky-500" />;
    }
    if (t.includes('buyer') || t.includes('supplier') || t.includes('organismo')) {
      return <Building2 className="w-4 h-4 text-amber-500" />;
    }
    return <Database className="w-4 h-4 text-purple-500" />;
  };

  const getSourceTypeLabel = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('tender') || t.includes('licitacion')) return 'Licitación';
    if (t.includes('order') || t.includes('oc')) return 'Orden de Compra';
    if (t.includes('supplier') || t.includes('proveedor')) return 'Proveedor';
    if (t.includes('buyer') || t.includes('organismo')) return 'Comprador';
    if (t.includes('mart')) return 'Data Mart SQL';
    return type;
  };

  return (
    <div className={`mt-4 border-t border-border pt-3 space-y-2 ${className}`}>
      <div className="flex items-center justify-between text-xs font-medium text-muted-foreground uppercase tracking-wider">
        <span>Fuentes y Citas Verificadas ({displayedSources.length})</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {displayedSources.map((item, idx) => {
          const isExpanded = !!expandedIds[item.id];
          const isCopied = copiedId === item.id;

          return (
            <div
              key={`${item.id}-${idx}`}
              className="group p-3 rounded-lg border border-border bg-card/60 hover:bg-card hover:border-primary/40 transition-all text-sm space-y-1.5"
            >
              {/* Card Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="p-1 rounded bg-muted">
                    {getSourceIcon(item.source_type)}
                  </div>
                  <span className="font-semibold truncate text-foreground" title={item.title}>
                    {item.title}
                  </span>
                </div>

                {item.score !== undefined && item.score !== null && (
                  <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono font-medium">
                    {Math.round(item.score * 100)}%
                  </span>
                )}
              </div>

              {/* Sub-header: ID, Type, Verified badge */}
              <div className="flex items-center flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="font-mono font-medium text-foreground/80">{item.id}</span>
                <span>•</span>
                <span>{getSourceTypeLabel(item.source_type)}</span>

                {item.is_verified ? (
                  <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                    <CheckCircle2 className="w-3 h-3" /> Verificado
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                    <AlertTriangle className="w-3 h-3" /> Sin evidencia
                  </span>
                )}

                <button
                  type="button"
                  onClick={(e) => copyToClipboard(item.id, item.id, e)}
                  className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-muted text-muted-foreground"
                  title="Copiar ID"
                >
                  {isCopied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>

              {/* Snippet preview & toggle */}
              {item.snippet && (
                <div className="pt-1">
                  <p className={`text-xs text-muted-foreground leading-relaxed ${isExpanded ? '' : 'line-clamp-2'}`}>
                    {item.snippet}
                  </p>
                  <button
                    type="button"
                    onClick={() => toggleExpand(item.id)}
                    className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline font-medium mt-1"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUp className="w-3 h-3" /> Menos detalles
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3 h-3" /> Ver extracto
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Navigation Action Link */}
              {(item.target_route || item.url) && (
                <div className="pt-1 flex items-center justify-end">
                  <a
                    href={item.target_route || item.url || '#'}
                    target={item.url ? '_blank' : '_self'}
                    rel={item.url ? 'noopener noreferrer' : undefined}
                    className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 font-medium transition-colors"
                  >
                    <span>Ver registro oficial</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
