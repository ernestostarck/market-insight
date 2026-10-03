import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts';
import { formatCLP } from '@/lib/formatters';

export interface TimeSeriesDataPoint {
  mes: string;
  monto: number;
  licitaciones: number;
}

interface TimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  height?: number;
  showLegend?: boolean;
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (active && payload && payload.length) {
    return (
      <div className="space-y-1 rounded-lg border border-border/80 bg-background/95 p-3 text-xs shadow-xl backdrop-blur-sm">
        <p className="mb-1.5 font-bold text-foreground">{label}</p>
        {payload.map((entry) => (
          <div key={entry.name} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
              {entry.name}:
            </span>
            <span className="font-mono font-semibold text-foreground">
              {entry.name === 'Monto Adjudicado' ? formatCLP(entry.value) : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
}

export function TimeSeriesChart({ data, height = 320, showLegend = true }: TimeSeriesChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center text-xs text-muted-foreground">
        No hay datos temporales disponibles para el período seleccionado.
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorMonto" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
              <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="colorLicitaciones" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.6} />

          <XAxis
            dataKey="mes"
            tickLine={false}
            axisLine={{ stroke: 'hsl(var(--border))' }}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
          />

          <YAxis
            yAxisId="left"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickFormatter={(value) => {
              if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(0)}B`;
              if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
              return `$${value}`;
            }}
          />

          <YAxis
            yAxisId="right"
            orientation="right"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
          />

          <Tooltip content={<CustomTooltip />} />
          {showLegend && <Legend verticalAlign="top" height={36} iconType="circle" />}

          <Area
            yAxisId="left"
            type="monotone"
            dataKey="monto"
            name="Monto Adjudicado"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorMonto)"
          />

          <Area
            yAxisId="right"
            type="monotone"
            dataKey="licitaciones"
            name="Licitaciones"
            stroke="#38bdf8"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorLicitaciones)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
