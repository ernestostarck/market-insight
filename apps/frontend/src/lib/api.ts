import { DEMO_MODE } from '@/lib/demo';
import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import { APP_CONFIG } from '@/lib/constants';
import { clearSession, installAuthHandling } from '@/lib/session';
import type { ApiError } from '@/types/common';
import { getSegmento } from '@/features/segmento/store';

export const apiClient: AxiosInstance = axios.create({
  baseURL: APP_CONFIG.apiBaseUrl,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Bearer token + transparent refresh-and-retry on 401 (must precede the error normaliser).
// Demo sin backend: toda llamada falla como error de red y cada pantalla usa sus datos de ejemplo.
if (DEMO_MODE) {
  apiClient.defaults.adapter = (config) =>
    Promise.reject(new AxiosError('Demo sin backend', AxiosError.ERR_NETWORK, config));
}

installAuthHandling(apiClient);

apiClient.interceptors.request.use(
  (config) => {
    // Scope every read to the rubro/concept picked on the Rubros page (endpoints that
    // don't support it ignore the param). An explicit `segmento` param wins.
    const segmento = getSegmento();
    if (segmento && (config.method ?? 'get').toLowerCase() === 'get') {
      config.params = { segmento: segmento.code, ...config.params };
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response Interceptor: Normalize Errors and Handle 401
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string | Array<{ msg: string; loc: string[] }> }>) => {
    let normalizedError: ApiError = {
      message: 'Ocurrió un error inesperado al comunicarse con el servidor.',
      status: error.response?.status,
    };

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      // Extract detail from FastAPI response format
      let detailMsg = '';
      if (typeof data?.detail === 'string') {
        detailMsg = data.detail;
      } else if (Array.isArray(data?.detail) && data.detail.length > 0) {
        detailMsg = data.detail.map((d) => d.msg).join('; ');
      }

      switch (status) {
        case 401:
          normalizedError = {
            message: detailMsg || 'Sesión expirada o credenciales inválidas.',
            status: 401,
            code: 'UNAUTHORIZED',
          };
          // A 401 that survived the refresh-and-retry means the session is really over
          // (a failed refresh already signalled it from lib/session.ts).
          if (
            typeof window !== 'undefined' &&
            (error.config as { _retriedAfterRefresh?: boolean } | undefined)?._retriedAfterRefresh
          ) {
            clearSession();
            window.dispatchEvent(new CustomEvent('auth:unauthorized'));
          }
          break;

        case 403:
          normalizedError = {
            message: detailMsg || 'No tienes permisos suficientes para realizar esta acción.',
            status: 403,
            code: 'FORBIDDEN',
          };
          break;

        case 404:
          normalizedError = {
            message: detailMsg || 'El recurso solicitado no fue encontrado.',
            status: 404,
            code: 'NOT_FOUND',
          };
          break;

        case 422:
          normalizedError = {
            message: detailMsg || 'Los datos enviados no son válidos.',
            status: 422,
            code: 'VALIDATION_ERROR',
            detail:
              typeof data?.detail === 'object'
                ? (data.detail as Record<string, unknown> | Array<unknown>)
                : undefined,
          };
          break;

        case 429:
          normalizedError = {
            message:
              'Demasiadas solicitudes. Por favor, espera unos instantes antes de reintentar.',
            status: 429,
            code: 'RATE_LIMITED',
          };
          break;

        case 500:
        case 502:
        case 503:
          normalizedError = {
            message:
              'Error en el servidor central de MercadoInsight. Por favor, intenta más tarde.',
            status,
            code: 'SERVER_ERROR',
          };
          break;

        default:
          normalizedError = {
            message: detailMsg || `Error HTTP ${status}`,
            status,
          };
      }
    } else if (error.code === 'ECONNABORTED') {
      normalizedError = {
        message: 'La solicitud tardó demasiado tiempo en responder (timeout).',
        code: 'TIMEOUT',
      };
    } else if (!error.response) {
      normalizedError = {
        message: 'No se pudo establecer conexión con el servidor. Revisa tu conexión a internet.',
        code: 'NETWORK_ERROR',
      };
    }

    return Promise.reject(normalizedError);
  },
);

/**
 * High-level API Service helper functions
 */
export const api = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.get<T>(url, config);
    return response.data;
  },
  post: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.post<T>(url, body, config);
    return response.data;
  },
  put: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.put<T>(url, body, config);
    return response.data;
  },
  patch: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.patch<T>(url, body, config);
    return response.data;
  },
  delete: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.delete<T>(url, config);
    return response.data;
  },
};
