import React from 'react';
import { NavLink } from 'react-router-dom';
import { ArrowRight, Building2, Calendar, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatCLP, formatDate } from '@/lib/formatters';
import type { Licitacion } from '@/types/licitacion';

interface RecentTendersTableProps {
  tenders: Licitacion[];
}

export function RecentTendersTable({ tenders }: RecentTendersTableProps) {
  const getStatusBadge = (estado?: string | null) => {
    switch (estado?.toLowerCase()) {
      case 'publicada':
        return <Badge variant="info">Publicada</Badge>;
      case 'adjudicada':
        return <Badge variant="success">Adjudicada</Badge>;
      case 'cerrada':
        return <Badge variant="secondary">Cerrada</Badge>;
      case 'desierta':
        return <Badge variant="destructive">Desierta</Badge>;
      default:
        return <Badge variant="outline">{estado || 'Sin estado'}</Badge>;
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">Licitaciones Recientes</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Últimas convocatorias abiertas y adjudicadas en ChileCompra
          </CardDescription>
        </div>
        <Button variant="ghost" size="sm" asChild className="gap-1 text-xs text-primary">
          <NavLink to="/licitaciones">
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
                <th className="px-4 py-2.5">Código</th>
                <th className="px-4 py-2.5">Licitación / Organismo</th>
                <th className="px-4 py-2.5 text-right">Monto Est.</th>
                <th className="px-4 py-2.5 text-center">Estado</th>
                <th className="px-4 py-2.5 text-right">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {tenders.map((tender) => (
                <tr
                  key={tender.id}
                  className="group cursor-pointer transition-colors hover:bg-muted/30"
                >
                  <td className="px-4 py-3 font-mono font-semibold text-primary">
                    <NavLink to={`/licitaciones/${tender.codigo}`} className="hover:underline">
                      {tender.codigo}
                    </NavLink>
                  </td>

                  <td className="max-w-xs px-4 py-3">
                    <p className="truncate font-medium text-foreground transition-colors group-hover:text-primary">
                      {tender.nombre}
                    </p>
                    <div className="mt-0.5 flex items-center gap-1 truncate text-[11px] text-muted-foreground">
                      <Building2 className="h-3 w-3 shrink-0" />
                      <span className="truncate">
                        {tender.organismo?.nombre || 'Organismo Público'}
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-3 text-right font-mono font-semibold text-foreground">
                    {formatCLP(tender.monto_estimado)}
                  </td>

                  <td className="px-4 py-3 text-center">{getStatusBadge(tender.estado)}</td>

                  <td className="whitespace-nowrap px-4 py-3 text-right text-muted-foreground">
                    <div className="flex items-center justify-end gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>{formatDate(tender.fecha_publicacion)}</span>
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
