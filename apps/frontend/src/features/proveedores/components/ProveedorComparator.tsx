import React, { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { X, Users, Plus, TrendingUp } from 'lucide-react';
import { formatCLP, formatRUT, formatCompactCurrency } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { Proveedor } from '@/types';
import { FALLBACK_PROVEEDORES } from '../hooks/useProveedores';

interface ProveedorComparatorProps {
  initialSuppliers?: Proveedor[];
  isOpen: boolean;
  onClose: () => void;
}

export const ProveedorComparator: React.FC<ProveedorComparatorProps> = ({
  initialSuppliers = [],
  isOpen,
  onClose,
}) => {
  const [selectedSuppliers, setSelectedSuppliers] = useState<Proveedor[]>(() => {
    if (initialSuppliers.length > 0) return initialSuppliers.slice(0, 3);
    return [FALLBACK_PROVEEDORES[0], FALLBACK_PROVEEDORES[1]];
  });
  const [isAdding, setIsAdding] = useState(false);

  if (!isOpen) return null;

  const handleRemove = (id: number) => {
    if (selectedSuppliers.length <= 1) return;
    setSelectedSuppliers((prev) => prev.filter((p) => p.id !== id));
  };

  const handleAdd = (p: Proveedor) => {
    if (selectedSuppliers.some((item) => item.id === p.id)) return;
    if (selectedSuppliers.length >= 3) {
      setSelectedSuppliers((prev) => [...prev.slice(1), p]);
    } else {
      setSelectedSuppliers((prev) => [...prev, p]);
    }
    setIsAdding(false);
  };

  const chartData = selectedSuppliers.map((s) => ({
    name: s.nombre_fantasia || s.razon_social?.slice(0, 18) || s.rut,
    monto: s.monto_total_adjudicado || 0,
    adjudicaciones: s.total_adjudicaciones || 0,
    tasa: s.tasa_exito || 0,
  }));

  const candidateSuppliers = FALLBACK_PROVEEDORES.filter(
    (cand) => !selectedSuppliers.some((s) => s.id === cand.id),
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in">
      <div className="relative max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-border/80 bg-card p-6 shadow-2xl text-card-foreground">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">
                Comparador Competitivo de Proveedores
              </h2>
              <p className="text-xs text-muted-foreground">
                Análisis comparativo cara a cara de hasta 3 empresas adjudicatarias de ChileCompra.
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 rounded-full p-0 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Action bar to add competitors */}
        <div className="my-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Proveedores en comparación:</span>
            <span className="rounded-full border border-border/80 bg-muted/60 px-2.5 py-0.5 text-xs font-semibold text-primary">
              {selectedSuppliers.length} / 3
            </span>
          </div>

          {selectedSuppliers.length < 3 && (
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAdding(!isAdding)}
                className="gap-1.5 border-primary/30 text-primary hover:bg-primary hover:text-white font-medium text-xs rounded-md shadow-sm transition-all"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Agregar Proveedor</span>
              </Button>

              {isAdding && (
                <div className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-border/80 bg-popover p-2 shadow-xl text-popover-foreground">
                  <span className="block px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                    Selecciona un competidor
                  </span>
                  <div className="mt-1 max-h-52 space-y-1 overflow-y-auto">
                    {candidateSuppliers.map((cand) => (
                      <button
                        key={cand.id}
                        onClick={() => handleAdd(cand)}
                        className="flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs text-foreground transition-colors hover:bg-muted"
                      >
                        <span className="truncate">{cand.razon_social}</span>
                        <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                          {formatRUT(cand.rut)}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Side by Side Comparative Cards */}
        <div className={`grid grid-cols-1 gap-4 md:grid-cols-${selectedSuppliers.length}`}>
          {selectedSuppliers.map((supplier) => (
            <Card
              key={supplier.id}
              className="relative rounded-xl border border-border/80 bg-card p-4 shadow-sm transition-all hover:border-primary/40"
            >
              {selectedSuppliers.length > 1 && (
                <button
                  onClick={() => handleRemove(supplier.id)}
                  className="absolute right-3 top-3 text-muted-foreground transition-colors hover:text-destructive"
                  title="Quitar de la comparación"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}

              <h4 className="truncate pr-6 text-sm font-bold text-foreground">
                {supplier.razon_social}
              </h4>
              <p className="mt-0.5 font-mono text-xs font-semibold text-primary">
                RUT: {formatRUT(supplier.rut)}
              </p>

              <div className="mt-4 space-y-2 border-t border-border/60 pt-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Monto Adjudicado:</span>
                  <strong className="font-mono text-emerald-600 dark:text-emerald-400">
                    {supplier.monto_total_adjudicado
                      ? formatCLP(supplier.monto_total_adjudicado)
                      : '$0 CLP'}
                  </strong>
                </div>

                <div className="flex justify-between">
                  <span className="text-muted-foreground">Adjudicaciones:</span>
                  <span className="font-semibold text-foreground">
                    {supplier.total_adjudicaciones} de {supplier.total_licitaciones_participadas}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Tasa de Éxito:</span>
                  <span className="rounded-full border border-emerald-500/20 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                    {supplier.tasa_exito != null ? `${supplier.tasa_exito.toFixed(1)}%` : '—'}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-muted-foreground">Categoría:</span>
                  <span className="max-w-[140px] truncate text-foreground font-medium">
                    {supplier.categoria_principal || 'Equipamiento Médico'}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-muted-foreground">Región:</span>
                  <span className="text-foreground font-medium">{supplier.region || 'Metropolitana'}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Comparative Chart */}
        <Card className="mt-6 rounded-xl border border-border/80 bg-card p-4 shadow-sm">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <TrendingUp className="h-4 w-4 text-primary" />
              <span>Contraste de Montos Adjudicados (CLP)</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 15, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(val) => formatCompactCurrency(val)}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="rounded-lg border border-border/80 bg-popover p-3 text-xs shadow-xl text-popover-foreground">
                            <p className="font-bold">{d.name}</p>
                            <p className="mt-1 font-mono text-primary font-semibold">
                              Monto: {formatCLP(d.monto)}
                            </p>
                            <p className="mt-0.5 text-muted-foreground">
                              Tasa éxito: {d.tasa}% ({d.adjudicaciones} contratos)
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                  <Bar
                    dataKey="monto"
                    name="Monto Adjudicado (CLP)"
                    fill="#0d6efd"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="border-border/80 bg-background text-xs font-medium text-foreground hover:bg-muted"
          >
            Cerrar Comparador
          </Button>
        </div>
      </div>
    </div>
  );
};
