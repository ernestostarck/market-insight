import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Info,
  RefreshCw,
  Server,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import type { ComponentHealth, ComponentStatus, SystemStatus } from '@/types/ai';

interface DataQualityCardProps {
  status: SystemStatus | undefined;
  isLoading?: boolean;
  isError?: boolean;
  onRefresh?: () => void;
}

const COMPONENT_LABELS: Record<string, string> = {
  api: 'API Backend',
  postgres: 'PostgreSQL',
  redis: 'Redis',
  minio: 'Almacenamiento (MinIO)',
  chilecompra: 'API ChileCompra',
};

function StatusBadge({ status }: { status: ComponentStatus }) {
  if (status === 'healthy') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
        Operativo
      </span>
    );
  }
  if (status === 'degraded') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30">
        <AlertCircle className="h-3 w-3 text-amber-500" />
        Degradado
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30">
      <XCircle className="h-3 w-3 text-red-500" />
      No disponible
    </span>
  );
}

export function DataQualityCard({ status, isLoading, isError, onRefresh }: DataQualityCardProps) {
  if (isError) {
    return (
      <div className="p-6 rounded-xl border border-red-500/30 bg-red-500/5 text-sm text-red-700 dark:text-red-300 flex items-center gap-3">
        <XCircle className="h-5 w-5 shrink-0" />
        <span>No se pudo obtener el estado del sistema (GET /system/status).</span>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="p-6 rounded-xl border border-border bg-card animate-pulse text-sm text-muted-foreground">
        Cargando estado del sistema...
      </div>
    );
  }

  const components = Object.entries(status.components) as [string, ComponentHealth][];

  return (
    <div className="space-y-6">
      {/* Real per-component health checks (app/monitoring/health.py) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {components.map(([key, component]) => (
          <div key={key} className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-primary" />
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  {COMPONENT_LABELS[key] ?? key}
                </span>
              </div>
              <StatusBadge status={component.status} />
            </div>
            <p className="text-xl font-bold text-foreground font-mono">
              {component.latency_ms != null ? component.latency_ms.toFixed(1) : '—'}{' '}
              <span className="text-sm font-normal text-muted-foreground">ms</span>
            </p>
            <span className="text-[11px] text-muted-foreground block truncate" title={component.message ?? ''}>
              {component.message ?? 'Sin mensaje'}
            </span>
          </div>
        ))}
      </div>

      {/* Real ETL freshness + Data Quality Score */}
      <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
          <div>
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Puntaje de Calidad de Datos
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Score consolidado (app/monitoring/metrics.py DATA_QUALITY_SCORE), evaluado por el pipeline ETL.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-extrabold text-foreground font-mono">
              {status.data_quality.score.toFixed(1)}%
            </span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isLoading}
                className="p-1.5 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                title="Actualizar estado"
                aria-label="Actualizar estado de calidad"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-sky-500 rounded-full transition-all duration-500"
              style={{ width: `${status.data_quality.score}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-muted-foreground">
            <span>Estado: {status.data_quality.status}</span>
            <span>Ambiente: {status.environment}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4 text-primary" />
            <span>Última sincronización ETL:</span>
            <span className="font-mono font-medium text-foreground">
              {status.etl.last_run_timestamp ?? 'Sin registro'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Activity className="h-4 w-4 text-primary" />
            <span>Antigüedad del dato más reciente:</span>
            <span className="font-medium text-foreground">
              {status.etl.data_freshness_seconds != null
                ? `${Math.round(status.etl.data_freshness_seconds / 3600)} h`
                : 'Sin registro'}
            </span>
          </div>
        </div>
      </div>

      {/* Explanatory copy on the platform's own data-quality doctrine (not live data) */}
      <div className="p-5 rounded-xl border border-primary/20 bg-primary/5 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-primary font-bold text-sm">
          <Info className="h-4 w-4" />
          Disponibilidad técnica y de datos, evaluadas por separado
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          La disponibilidad <strong className="text-foreground">técnica</strong> (¿puede la plataforma servir
          solicitudes?) y la disponibilidad de <strong className="text-foreground">datos</strong> (¿está la
          información vigente y confiable?) se evalúan de forma independiente: la plataforma puede estar técnicamente
          arriba con datos desactualizados, o viceversa.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div className="p-3 rounded-lg border border-border bg-card text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground">Técnica</span>
              <StatusBadge status={status.availability.technical.status} />
            </div>
            {status.availability.technical.reasons.length > 0 ? (
              <ul className="list-disc pl-4 text-[11px] text-muted-foreground space-y-0.5">
                {status.availability.technical.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="text-[11px] text-muted-foreground">Sin incidencias.</p>
            )}
          </div>
          <div className="p-3 rounded-lg border border-border bg-card text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground">Datos</span>
              <StatusBadge status={status.availability.data.status} />
            </div>
            {status.availability.data.reasons.length > 0 ? (
              <ul className="list-disc pl-4 text-[11px] text-muted-foreground space-y-0.5">
                {status.availability.data.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="text-[11px] text-muted-foreground">Sin incidencias.</p>
            )}
          </div>
        </div>
      </div>

      {/* Real reasons surfaced above already cover what used to be fabricated "advertencias" */}
      {(status.availability.technical.reasons.length > 0 || status.availability.data.reasons.length > 0) && (
        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400">
            <ShieldAlert className="h-4 w-4 shrink-0" />
            Incidencias activas
          </div>
          <ul className="space-y-1.5 pl-6 list-disc text-xs text-muted-foreground">
            {[...status.availability.technical.reasons, ...status.availability.data.reasons].map((reason) => (
              <li key={reason} className="text-[11px]">
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
