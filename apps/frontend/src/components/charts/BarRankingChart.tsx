import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts';
import { formatCLP } from '@/lib/formatters';

export interface RankingItem {
  name: string;
  value: number;
  secondaryValue?: number;
  label?: string;
}

interface BarRankingChartProps {
  data: RankingItem[];
  height?: number;
  barColor?: string;
  valueIsCurrency?: boolean;
}

const PALETTE = ['hsl(var(--primary))', '#38bdf8', '#818cf8', '#a78bfa', '#c084fc'];

export function BarRankingChart({
  data,
  height = 280,
  valueIsCurrency = true,
}: BarRankingChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center text-xs text-muted-foreground">
        Sin datos de ranking disponibles.
      </div>
    );
  }

  function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
    if (active && payload && payload.length) {
      const item = payload[0].payload as RankingItem;
      return (
        <div className="space-y-1 rounded-lg border border-border/80 bg-background/95 p-3 text-xs shadow-xl backdrop-blur-sm">
          <p className="font-bold text-foreground">{item.name}</p>
          <p className="font-mono font-semibold text-primary">
            {valueIsCurrency ? formatCLP(item.value) : item.value}
          </p>
          {item.label && <p className="text-[10px] text-muted-foreground">{item.label}</p>}
        </div>
      );
    }
    return null;
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="hsl(var(--border))"
            opacity={0.6}
          />

          <XAxis
            type="number"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
            tickFormatter={(val) => {
              if (!valueIsCurrency) return String(val);
              if (val >= 1_000_000_000) return `$${(val / 1_000_000_000).toFixed(0)}B`;
              if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(0)}M`;
              return `$${val}`;
            }}
          />

          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: 'hsl(var(--foreground))' }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
