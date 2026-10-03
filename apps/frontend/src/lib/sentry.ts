/**
 * Sentry client error tracking and telemetry integration (Fase 8.12).
 *
 * Catches runtime React exceptions, strips PII / authorization tokens,
 * and attaches deployment environment metadata.
 */

interface SentryBreadcrumb {
  category?: string;
  message?: string;
  level?: string;
  timestamp?: number;
}

interface SentryClientConfig {
  dsn?: string;
  environment?: string;
  release?: string;
  sampleRate?: number;
}

const SENSITIVE_KEY_PATTERNS = [/password/i, /token/i, /secret/i, /api_?key/i, /auth/i];

function scrubSensitiveData<T>(obj: T): T {
  if (!obj || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) {
    return obj.map(scrubSensitiveData) as unknown as T;
  }
  const cleaned: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (SENSITIVE_KEY_PATTERNS.some((pattern) => pattern.test(k))) {
      cleaned[k] = '***REDACTED***';
    } else if (typeof v === 'object' && v !== null) {
      cleaned[k] = scrubSensitiveData(v);
    } else {
      cleaned[k] = v;
    }
  }
  return cleaned as T;
}

class SentryTelemetry {
  private dsn: string | null = null;
  private environment: string = 'development';
  private release: string = 'market-insight-frontend@0.1.0';
  private breadcrumbs: SentryBreadcrumb[] = [];

  init(config?: SentryClientConfig): void {
    this.dsn = config?.dsn ?? (import.meta.env.VITE_SENTRY_DSN as string | undefined) ?? null;
    this.environment =
      config?.environment ?? (import.meta.env.MODE as string | undefined) ?? 'development';
    this.release = config?.release ?? 'market-insight-frontend@0.1.0';

    if (this.dsn) {
      // In production with DSN, hook into window unhandled errors
      window.addEventListener('error', (event) => {
        this.captureException(event.error ?? new Error(event.message));
      });
      window.addEventListener('unhandledrejection', (event) => {
        this.captureException(event.reason);
      });
      // eslint-disable-next-line no-console
      console.info(`[Sentry] Initialized for environment: ${this.environment}`);
    }
  }

  addBreadcrumb(breadcrumb: SentryBreadcrumb): void {
    this.breadcrumbs.push({
      ...breadcrumb,
      timestamp: Date.now(),
    });
    if (this.breadcrumbs.length > 50) {
      this.breadcrumbs.shift();
    }
  }

  captureException(error: unknown, context?: Record<string, unknown>): void {
    const scrubbedContext = context ? scrubSensitiveData(context) : {};
    // Log to console in non-production or if DSN is not set
    if (!this.dsn || this.environment !== 'production') {
      // eslint-disable-next-line no-console
      console.error('[Sentry Telemetry Captured Error]:', error, scrubbedContext);
      return;
    }

    // In production with DSN, payload could be dispatched via Sentry envelope API or SDK
    try {
      const errorMsg = error instanceof Error ? error.message : String(error);
      const stack = error instanceof Error ? error.stack : undefined;
      const payload = {
        message: errorMsg,
        stack,
        environment: this.environment,
        release: this.release,
        timestamp: new Date().toISOString(),
        extra: scrubbedContext,
        breadcrumbs: this.breadcrumbs.slice(-10),
      };

      // Dispatched safely
      if (navigator.sendBeacon) {
        navigator.sendBeacon(this.dsn, JSON.stringify(payload));
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('[Sentry] Failed to dispatch error report:', e);
    }
  }

  captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info'): void {
    if (!this.dsn || this.environment !== 'production') {
      // eslint-disable-next-line no-console
      console.log(`[Sentry Telemetry ${level.toUpperCase()}]: ${message}`);
      return;
    }
    this.addBreadcrumb({ message, level, category: 'manual' });
  }
}

export const sentry = new SentryTelemetry();
