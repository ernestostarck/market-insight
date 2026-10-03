import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CursorPaginationProps {
  total: number;
  pageSize: number;
  pageNumber: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onNext: () => void;
  onPrevious: () => void;
  onPageSizeChange?: (size: number) => void;
  isLoading?: boolean;
}

export const CursorPagination: React.FC<CursorPaginationProps> = ({
  total,
  pageSize,
  pageNumber,
  hasNext,
  hasPrevious,
  onNext,
  onPrevious,
  onPageSizeChange,
  isLoading,
}) => {
  const startRange = total === 0 ? 0 : (pageNumber - 1) * pageSize + 1;
  const endRange = Math.min(pageNumber * pageSize, total);

  return (
    <div className="flex flex-col items-center justify-between gap-4 border-t border-border px-5 py-3.5 sm:flex-row bg-muted/10">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>
          Mostrando{' '}
          <strong className="font-bold text-foreground">
            {startRange} - {endRange}
          </strong>{' '}
          de <strong className="font-bold text-foreground">{total}</strong> licitaciones
        </span>

        {onPageSizeChange && (
          <div className="flex items-center gap-1.5 pl-2">
            <span className="hidden sm:inline">Por pág:</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              disabled={isLoading}
              className="rounded-md border border-border bg-background px-2.5 py-1 text-xs font-semibold text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary shadow-2xs cursor-pointer"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2.5">
        <span className="mr-1 text-xs text-muted-foreground">
          Página <strong className="font-bold text-foreground">{pageNumber}</strong>
        </span>

        <Button
          variant="outline"
          size="sm"
          onClick={onPrevious}
          disabled={!hasPrevious || isLoading}
          className="flex items-center gap-1 border-border/80 bg-background text-foreground hover:bg-muted text-xs font-semibold rounded-md shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          <span>Anterior</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={!hasNext || isLoading}
          className="flex items-center gap-1 border-border/80 bg-background text-foreground hover:bg-muted text-xs font-semibold rounded-md shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-40"
        >
          <span>Siguiente</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
};
