import React from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { Layers, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface GenericModulePageProps {
  title?: string;
  description?: string;
}

export function GenericModulePage({ title, description }: GenericModulePageProps) {
  const params = useParams();
  const location = useLocation();

  const segment = location.pathname.split('/').filter(Boolean)[0] || 'modulo';
  const displayTitle =
    title || segment.charAt(0).toUpperCase() + segment.slice(1).replace('-', ' ');

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{displayTitle}</h1>
            <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
              {description ||
                `Vista analítica y de consulta para ${displayTitle.toLowerCase()} de ChileCompra.`}
            </p>
          </div>

          {params.id && (
            <Badge variant="secondary" className="font-mono text-xs self-start sm:self-auto">
              ID / Código: {params.id}
            </Badge>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-primary" />
            <CardTitle>Módulo de {displayTitle}</CardTitle>
          </div>
          <CardDescription>
            Ruta activa: <code className="font-mono text-xs text-primary">{location.pathname}</code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-dashed border-border/80 bg-muted/20 p-8 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">
              Explorador y Datos del Dominio
            </h3>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              La arquitectura de enrutamiento y sesión está conectada. Los datos y tablas de este
              módulo se integrarán en las subfases 7.10–7.18.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
