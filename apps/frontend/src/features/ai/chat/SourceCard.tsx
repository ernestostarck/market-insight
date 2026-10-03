import React, { useState } from 'react';
import { ExternalLink, FileText, ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react';
import { SourceItem } from './types';

interface SourceCardProps {
  source: SourceItem;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border/70 bg-card p-2.5 text-xs transition-all hover:border-primary/40 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 font-medium text-foreground">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
            {index + 1}
          </span>
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="truncate max-w-[160px] sm:max-w-[220px]" title={source.title}>
            {source.title || `Documento ${source.id}`}
          </span>
        </div>

        {source.relevance_score !== undefined && (
          <span className="shrink-0 flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="h-3 w-3" />
            {(source.relevance_score * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {source.organismo && (
        <p className="mt-1 text-[11px] text-muted-foreground truncate">
          {source.organismo}
        </p>
      )}

      {source.chunk_text && (
        <div className="mt-2 pt-2 border-t border-border/50">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-[10px] font-medium text-primary hover:underline"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? 'Ocultar fragmento' : 'Ver fragmento de evidencia'}
          </button>
          {expanded && (
            <p className="mt-1.5 text-[11px] text-muted-foreground italic bg-muted/40 p-2 rounded border border-border/40 leading-relaxed font-sans">
              "{source.chunk_text}"
            </p>
          )}
        </div>
      )}

      {source.id && (
        <div className="mt-2 flex justify-end">
          <a
            href={`/licitaciones/${source.id}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground hover:underline"
          >
            Ficha oficial
            <ExternalLink className="h-2.5 w-2.5" />
          </a>
        </div>
      )}
    </div>
  );
};
