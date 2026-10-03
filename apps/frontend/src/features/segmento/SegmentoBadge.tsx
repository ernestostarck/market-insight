import { Link } from 'react-router-dom';
import { Layers, X } from 'lucide-react';
import { setSegmento, useSegmento } from './store';

/** Header pill showing the active rubro/concept; the × clears it. */
export function SegmentoBadge() {
  const segmento = useSegmento();
  if (!segmento) return null;

  return (
    <div className="flex max-w-[16rem] items-center gap-1 rounded-full border border-primary/30 bg-primary/10 py-0.5 pl-2.5 pr-1 text-[11px] font-medium text-primary">
      <Layers className="h-3 w-3 shrink-0" />
      <Link
        to="/rubros"
        className="truncate hover:underline"
        title={
          segmento.parentLabel ? `${segmento.parentLabel} › ${segmento.label}` : segmento.label
        }
      >
        Rubro: {segmento.label}
      </Link>
      <button
        type="button"
        onClick={() => setSegmento(null)}
        className="rounded-full p-0.5 hover:bg-primary/20"
        aria-label="Quitar rubro seleccionado"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}
