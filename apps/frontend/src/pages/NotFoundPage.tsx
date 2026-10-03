import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-500">
        <AlertTriangle className="h-8 w-8" />
      </div>

      <h1 className="text-4xl font-extrabold tracking-tight text-foreground">404</h1>
      <h2 className="mt-2 text-xl font-bold text-foreground">Página no encontrada</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        La ruta a la que intentas acceder no existe o fue trasladada a otra sección del portal de
        inteligencia.
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button variant="outline" size="sm" onClick={() => navigate(-1)} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Volver atrás
        </Button>
        <Button size="sm" onClick={() => navigate('/dashboard')} className="gap-2">
          <Home className="h-4 w-4" />
          Ir al Dashboard
        </Button>
      </div>
    </div>
  );
}
