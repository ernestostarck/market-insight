import React from 'react';
import { Layers } from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import { formatCLP } from '@/lib/formatters';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { AdvancedAnalyticsData } from '../hooks/useAdvancedAnalytics';

interface CategoryAnalysisTabProps {
  data: AdvancedAnalyticsData['categoryAnalysis'];
}

export const CategoryAnalysisTab: React.FC<CategoryAnalysisTabProps> = ({ data }) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Pie Chart */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Layers className="h-4 w-4 text-primary" />
              <span>Distribución Porcentual del Gasto Asistencial</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.distribucion}
                    dataKey="monto"
                    nameKey="categoria"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                  >
                    {data.distribucion.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="rounded-lg border border-border/80 bg-popover p-2.5 text-xs shadow-xl text-popover-foreground">
                            <p className="font-bold">{d.categoria}</p>
                            <p className="mt-1 font-mono text-primary font-semibold">
                              {formatCLP(d.monto)} ({d.porcentaje}%)
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Breakdown List */}
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="text-sm font-semibold text-foreground">
              Desglose de Montos por Rubro
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 p-0 pt-2">
            {data.distribucion.map((cat, idx) => (
              <div key={idx} className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: cat.color }}
                    />
                    <span className="font-semibold text-foreground">{cat.categoria}</span>
                  </div>
                  <span className="font-mono text-muted-foreground font-medium">
                    {cat.porcentaje}% • {formatCLP(cat.monto)}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${cat.porcentaje}%`,
                      backgroundColor: cat.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
