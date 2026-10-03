import React from 'react';
import { Users, Award, ShieldAlert } from 'lucide-react';
import { formatCLP, formatRUT } from '@/lib/formatters';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { AdvancedAnalyticsData } from '../hooks/useAdvancedAnalytics';

interface SupplierAnalysisTabProps {
  data: AdvancedAnalyticsData['supplierAnalysis'];
}

export const SupplierAnalysisTab: React.FC<SupplierAnalysisTabProps> = ({ data }) => {
  return (
    <div className="space-y-6">
      {/* Concentration KPI Card */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Índice de Concentración (HHI)
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
              <ShieldAlert className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-3 font-mono text-2xl font-bold text-primary">
            {data.indiceHHI != null ? Math.round(data.indiceHHI) : '—'}
          </p>
          <span className="mt-1 block text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            {data.nivelConcentracion}
          </span>
        </Card>

        <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Cuota Acumulada Top 3
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-3 font-mono text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {(
              data.topProveedores.slice(0, 3).reduce((acc, p) => acc + p.cuota, 0)
            ).toFixed(1)}
            %
          </p>
          <span className="mt-1 block text-xs text-muted-foreground">
            Suma de la cuota de mercado de los 3 principales proveedores por monto adjudicado
          </span>
        </Card>
      </div>

      {/* Top Suppliers Table */}
      <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <CardHeader className="border-b border-border/80 p-4">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Users className="h-4 w-4 text-primary" />
            <span>Ranking de Cuota y Efectividad de Adjudicación</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-foreground">
              <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Proveedor / Razón Social</th>
                  <th className="px-4 py-3">RUT</th>
                  <th className="px-4 py-3 text-right">Monto Adjudicado</th>
                  <th className="px-4 py-3">Cuota de Mercado</th>
                  <th className="px-4 py-3 text-center">Ratio Adjudicación</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 bg-card">
                {data.topProveedores.map((p, idx) => (
                  <tr key={idx} className="group transition-colors hover:bg-muted/40">
                    <td className="max-w-xs px-4 py-3 font-semibold text-foreground">
                      {p.razon_social}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-muted-foreground">
                      {formatRUT(p.rut)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      {formatCLP(p.monto)}
                    </td>
                    <td className="min-w-[140px] px-4 py-3">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="font-mono font-semibold text-primary">{p.cuota.toFixed(1)}%</span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full bg-primary"
                            style={{ width: `${Math.min(100, p.cuota * 3)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {p.ratioAdjudicacionPromedio != null ? (
                        <span className="inline-flex rounded-full border border-emerald-500/20 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                          {p.ratioAdjudicacionPromedio.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
