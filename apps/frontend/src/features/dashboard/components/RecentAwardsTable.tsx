import React from 'react';
import { NavLink } from 'react-router-dom';
import { ArrowRight, Award, Building2, Calendar, UserCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCLP, formatDate, formatRUT } from '@/lib/formatters';
import type { Adjudicacion } from '@/types/adjudicacion';

interface RecentAwardsTableProps {
  awards: Adjudicacion[];
}

export function RecentAwardsTable({ awards }: RecentAwardsTableProps) {
  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Award className="h-4 w-4 text-emerald-500" />
            <CardTitle className="text-base">Últimas Adjudicaciones</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Contratos adjudicados y montos de cierre en compras públicas
          </CardDescription>
        </div>
        <Button variant="ghost" size="sm" asChild className="gap-1 text-xs text-primary">
          <NavLink to="/adjudicaciones">
            Ver todas
            <ArrowRight className="h-3.5 w-3.5" />
          </NavLink>
        </Button>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-y border-border/80 bg-muted/40 font-semibold text-muted-foreground">
                <th className="px-4 py-2.5">Licitación</th>
                <th className="px-4 py-2.5">Adjudicatario</th>
                <th className="px-4 py-2.5 text-right">Monto Adjudicado</th>
                <th className="px-4 py-2.5 text-right">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {awards.map((award) => (
                <tr
                  key={award.id}
                  className="group cursor-pointer transition-colors hover:bg-muted/30"
                >
                  <td className="max-w-xs px-4 py-3">
                    <p className="truncate font-mono font-semibold text-primary">
                      {award.licitacion_codigo}
                    </p>
                    <p className="mt-0.5 truncate font-medium text-foreground">
                      {award.licitacion_nombre}
                    </p>
                    <div className="mt-0.5 flex items-center gap-1 truncate text-[11px] text-muted-foreground">
                      <Building2 className="h-3 w-3 shrink-0" />
                      <span className="truncate">{award.organismo_nombre}</span>
                    </div>
                  </td>

                  <td className="max-w-xs px-4 py-3">
                    <div className="flex items-center gap-1.5 font-medium text-foreground">
                      <UserCheck className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                      <span className="truncate">{award.proveedor_razon_social}</span>
                    </div>
                    <span className="ml-5 font-mono text-[11px] text-muted-foreground">
                      RUT: {formatRUT(award.proveedor_rut)}
                    </span>
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {formatCLP(award.monto_adjudicado)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-right text-muted-foreground">
                    <div className="flex items-center justify-end gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>{formatDate(award.fecha_adjudicacion)}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
