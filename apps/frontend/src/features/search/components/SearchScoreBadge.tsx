import React from 'react';
import { Sparkles, KeyRound } from 'lucide-react';

interface SearchScoreBadgeProps {
  score: number;
  semanticScore?: number;
  keywordScore?: number;
}

export const SearchScoreBadge: React.FC<SearchScoreBadgeProps> = ({
  score,
  semanticScore,
  keywordScore,
}) => {
  const finalPercent = Math.round(score * 100);

  return (
    <div className="flex flex-col items-start gap-2 text-xs sm:flex-row sm:items-center">
      {/* Final Hybrid Score */}
      <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-950/60 px-2.5 py-0.5 font-semibold text-emerald-300">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        <span>{finalPercent}% Match Híbrido</span>
      </div>

      {/* Semantic vs Keyword Breakdown */}
      {(semanticScore !== undefined || keywordScore !== undefined) && (
        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          {semanticScore !== undefined && (
            <span className="inline-flex items-center gap-1 rounded border border-slate-700/60 bg-slate-800/80 px-2 py-0.5 text-cyan-300">
              <Sparkles className="h-2.5 w-2.5" />
              <span>Semántico: {Math.round(semanticScore * 100)}%</span>
            </span>
          )}
          {keywordScore !== undefined && (
            <span className="inline-flex items-center gap-1 rounded border border-slate-700/60 bg-slate-800/80 px-2 py-0.5 text-amber-300">
              <KeyRound className="h-2.5 w-2.5" />
              <span>Keyword: {Math.round(keywordScore * 100)}%</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};
