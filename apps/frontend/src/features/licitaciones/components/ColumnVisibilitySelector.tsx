import React, { useState, useRef, useEffect } from 'react';
import { SlidersHorizontal, Check, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ColumnDefinition {
  id: string;
  label: string;
  visible: boolean;
  required?: boolean;
}

interface ColumnVisibilitySelectorProps {
  columns: ColumnDefinition[];
  onToggleColumn: (columnId: string) => void;
  onResetColumns: () => void;
}

export const ColumnVisibilitySelector: React.FC<ColumnVisibilitySelectorProps> = ({
  columns,
  onToggleColumn,
  onResetColumns,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const visibleCount = columns.filter((c) => c.visible).length;

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 border-border/80 bg-background text-foreground hover:bg-muted font-medium text-xs rounded-md shadow-sm transition-all"
        title="Personalizar columnas visibles"
      >
        <SlidersHorizontal className="h-3.5 w-3.5 text-primary" />
        <span>Columnas</span>
        <span className="ml-1 rounded-full bg-muted border border-border/60 px-1.5 py-0.2 text-xs font-semibold text-muted-foreground">
          {visibleCount}/{columns.length}
        </span>
      </Button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-2 w-64 origin-top-right rounded-lg border border-border bg-card p-3 shadow-xl ring-1 ring-black/5 animate-in fade-in zoom-in-95">
          <div className="mb-2 flex items-center justify-between border-b border-border pb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Columnas Visibles
            </span>
            <button
              onClick={onResetColumns}
              className="flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline cursor-pointer"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Restablecer</span>
            </button>
          </div>

          <div className="space-y-1 py-1">
            {columns.map((col) => (
              <button
                key={col.id}
                onClick={() => onToggleColumn(col.id)}
                disabled={col.required}
                className={`flex w-full items-center justify-between rounded px-2.5 py-1.5 text-left text-xs transition-colors cursor-pointer ${
                  col.visible
                    ? 'font-semibold text-foreground hover:bg-muted'
                    : 'text-muted-foreground hover:bg-muted/60'
                } ${col.required ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                <span>{col.label}</span>
                {col.visible && <Check className="h-3.5 w-3.5 text-primary" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
