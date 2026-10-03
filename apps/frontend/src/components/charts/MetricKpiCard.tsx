import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export interface MetricKpiCardProps {
  title: string;
  value: string | number;
  change?: number; // e.g. 12.5 for +12.5%
  changeLabel?: string; // e.g. "vs mes anterior"
  icon?: React.ComponentType<{ className?: string }>;
  helper?: string;
  badge?: string;
  className?: string;
}

export function MetricKpiCard({
  title,
  value,
  change,
  changeLabel = 'vs mes anterior',
  icon: Icon,
  helper,
  badge,
  className,
}: MetricKpiCardProps) {
  const isPositive = change !== undefined && change > 0;
  const isNegative = change !== undefined && change < 0;
  const isNeutral = change !== undefined && change === 0;

  return (
    <Card
      className={cn(
        'relative overflow-hidden transition-all duration-200 hover:shadow-md',
        className,
      )}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {title}
          </span>
          {Icon && (
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="h-4 w-4" />
            </div>
          )}
        </div>

        <div className="mt-3 flex items-baseline justify-between gap-2">
          <div className="font-mono text-2xl font-extrabold tracking-tight text-foreground">
            {value}
          </div>
          {badge && (
            <span className="rounded bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
              {badge}
            </span>
          )}
        </div>

        {/* Trend Indicator */}
        {change !== undefined && (
          <div className="mt-2.5 flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                'inline-flex items-center rounded-full px-1.5 py-0.5 text-[11px] font-semibold leading-none',
                isPositive && 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
                isNegative && 'bg-destructive/15 text-destructive',
                isNeutral && 'bg-muted text-muted-foreground',
              )}
            >
              {isPositive && <ArrowUpRight className="mr-0.5 h-3 w-3" />}
              {isNegative && <ArrowDownRight className="mr-0.5 h-3 w-3" />}
              {isNeutral && <Minus className="mr-0.5 h-3 w-3" />}
              {Math.abs(change)}%
            </span>
            <span className="text-[11px] text-muted-foreground">{changeLabel}</span>
          </div>
        )}

        {helper && (
          <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{helper}</p>
        )}
      </CardContent>
    </Card>
  );
}
