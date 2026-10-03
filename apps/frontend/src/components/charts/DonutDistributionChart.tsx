import React from 'react';
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
} from 'recharts';

export interface DistributionItem {
  name: string;
  value: number;
  color?: string;
}

interface DonutDistributionChartProps {
  data: DistributionItem[];
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
}

const DEFAULT_COLORS = [
  'hsl(var(--primary))',
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#06b6d4', // cyan
];

export function DonutDistributionChart({
  data,
  height = 280,
  innerRadius = 55,
  outerRadius = 85,
}: DonutDistributionChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center text-xs text-muted-foreground">
        Sin datos de distribución disponibles.
      </div>
    );
  }

  const total = data.reduce((sum, item) => sum + item.value, 0);

  function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
    if (active && payload && payload.length) {
      const item = payload[0];
      const val = Number(item.value);
      const percentage = total > 0 ? ((val / total) * 100).toFixed(1) : '0';

      return (
        <div className="space-y-1 rounded-lg border border-border/80 bg-background/95 p-2.5 text-xs shadow-xl backdrop-blur-sm">
          <p className="font-bold text-foreground">{item.name}</p>
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold text-primary">{val} licitaciones</span>
            <span className="text-muted-foreground">({percentage}%)</span>
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            formatter={(val) => <span className="text-xs text-foreground">{val}</span>}
          />
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                stroke="hsl(var(--background))"
                strokeWidth={2}
              />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
