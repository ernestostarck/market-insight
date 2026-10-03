import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Database,
  Cpu,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface ComponentDetail {
  status: 'healthy' | 'degraded' | 'unhealthy';
  message?: string;
  latency_ms?: number;
}

interface SystemStatusData {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  app_name: string;
  version: string;
  environment: string;
  components: Record<string, ComponentDetail>;
  etl: {
    status: 'healthy' | 'stale' | 'failed';
    last_run_timestamp?: string;
    data_freshness_seconds?: number;
  };
  data_quality: {
    score: number;
    status: 'healthy' | 'degraded' | 'critical';
    last_evaluated?: string;
  };
}

export function SystemStatusBar() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery<SystemStatusData>({
    queryKey: ['system-status'],
    queryFn: async () => {
      const res = await apiClient.get<SystemStatusData>('/system/status');
      return res.data;
    },
    refetchInterval: 30000, // 30s auto polling
  });

  if (isLoading) {
    return (
      <div className="flex h-10 w-full animate-pulse items-center justify-between rounded-lg border border-border/40 bg-card/40 px-4">
        <span className="text-xs text-muted-foreground">Verificando estado del sistema...</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex w-full items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-400">
        <div className="flex items-center gap-2">
          <XCircle className="h-4 w-4" />
          <span>No se pudo obtener el estado operacional del sistema</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          className="h-7 text-xs text-red-300 hover:bg-red-500/20"
        >
          <RefreshCw className="mr-1 h-3 w-3" /> Reintentar
        </Button>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
      case 'degraded':
      case 'stale':
        return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
      default:
        return 'text-red-400 border-red-500/30 bg-red-500/10';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
      case 'degraded':
      case 'stale':
        return <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />;
      default:
        return <XCircle className="h-3.5 w-3.5 text-red-400" />;
    }
  };

  const freshnessHours = data.etl.data_freshness_seconds
    ? (data.etl.data_freshness_seconds / 3600).toFixed(1)
    : null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/50 bg-card/60 p-3 shadow-sm backdrop-blur-md">
      <div className="flex flex-wrap items-center gap-3">
        {/* Global System Status */}
        <div className="flex items-center gap-2 pr-2 border-r border-border/40">
          <div className="relative flex h-2.5 w-2.5">
            <span
              className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                data.status === 'healthy'
                  ? 'bg-emerald-400'
                  : data.status === 'degraded'
                    ? 'bg-amber-400'
                    : 'bg-red-400'
              }`}
            />
            <span
              className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                data.status === 'healthy'
                  ? 'bg-emerald-500'
                  : data.status === 'degraded'
                    ? 'bg-amber-500'
                    : 'bg-red-500'
              }`}
            />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
            Sistema {data.status === 'healthy' ? 'Operacional' : data.status}
          </span>
        </div>

        {/* Database */}
        <Badge
          variant="outline"
          className={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] ${getStatusColor(
            data.components.postgres?.status ?? 'unhealthy',
          )}`}
        >
          <Database className="h-3 w-3" />
          <span>Postgres</span>
          {data.components.postgres?.latency_ms !== undefined && (
            <span className="opacity-75">({data.components.postgres.latency_ms}ms)</span>
          )}
        </Badge>

        {/* Redis */}
        <Badge
          variant="outline"
          className={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] ${getStatusColor(
            data.components.redis?.status ?? 'unhealthy',
          )}`}
        >
          <Cpu className="h-3 w-3" />
          <span>Redis</span>
          {data.components.redis?.latency_ms !== undefined && (
            <span className="opacity-75">({data.components.redis.latency_ms}ms)</span>
          )}
        </Badge>

        {/* ChileCompra API */}
        <Badge
          variant="outline"
          className={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] ${getStatusColor(
            data.components.chilecompra?.status ?? 'degraded',
          )}`}
        >
          {getStatusIcon(data.components.chilecompra?.status ?? 'degraded')}
          <span>ChileCompra API</span>
        </Badge>

        {/* Data Quality Score */}
        <Badge
          variant="outline"
          className={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] ${getStatusColor(
            data.data_quality.status,
          )}`}
        >
          <Sparkles className="h-3 w-3" />
          <span>Calidad: {data.data_quality.score}%</span>
        </Badge>

        {/* ETL Freshness */}
        {freshnessHours && (
          <Badge
            variant="outline"
            className={`flex items-center gap-1 px-2.5 py-1 text-[11px] ${getStatusColor(
              data.etl.status,
            )}`}
          >
            <Activity className="h-3 w-3" />
            <span>Frescura: {freshnessHours}h</span>
          </Badge>
        )}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-[11px] text-muted-foreground">v{data.version}</span>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => refetch()}
          disabled={isFetching}
          className="h-7 w-7 text-muted-foreground hover:text-foreground"
          title="Actualizar estado del sistema"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
        </Button>
      </div>
    </div>
  );
}
