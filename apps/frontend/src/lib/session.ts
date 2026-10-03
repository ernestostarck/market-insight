import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { STORAGE_KEYS } from '@/lib/constants';

/**
 * Session handling for the hardened backend:
 * - The access token is short-lived (15 min) and kept in localStorage.
 * - The refresh token lives in an httpOnly cookie the browser sends only to
 *   /api/v1/auth/*; JavaScript never sees it.
 * - The access token is renewed proactively a minute before it expires, and
 *   reactively when a request gets a 401 (the request is then retried once).
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
const REFRESH_MARGIN_MS = 60_000;

let refreshInFlight: Promise<string | null> | null = null;
let refreshTimer: ReturnType<typeof setTimeout> | null = null;

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEYS.authToken);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string, expiresInSeconds?: number | null): void {
  try {
    localStorage.setItem(STORAGE_KEYS.authToken, token);
  } catch {
    // Storage unavailable: the in-flight requests still carry the header.
  }
  if (expiresInSeconds) scheduleRefresh(expiresInSeconds);
}

export function clearSession(): void {
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = null;
  try {
    localStorage.removeItem(STORAGE_KEYS.authToken);
  } catch {
    // ignore
  }
}

function scheduleRefresh(expiresInSeconds: number): void {
  if (refreshTimer) clearTimeout(refreshTimer);
  const delay = Math.max(expiresInSeconds * 1000 - REFRESH_MARGIN_MS, 5_000);
  refreshTimer = setTimeout(() => {
    void refreshAccessToken();
  }, delay);
}

/** Exchange the httpOnly refresh cookie for a new access token (deduplicated). */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = axios
      .post<{ access_token: string; expires_in?: number }>(`${API_BASE}/auth/refresh`, null, {
        withCredentials: true,
        timeout: 15_000,
      })
      .then((response) => {
        setAccessToken(response.data.access_token, response.data.expires_in);
        return response.data.access_token;
      })
      .catch(() => {
        clearSession();
        if (typeof window !== 'undefined')
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        return null;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

const AUTH_ENDPOINTS = ['/auth/login', '/auth/refresh', '/auth/mfa/verify', '/auth/logout'];

type RetriableConfig = InternalAxiosRequestConfig & { _retriedAfterRefresh?: boolean };

/**
 * Attach the bearer token to every request and, on a 401, refresh once and retry.
 * Must be installed before any error-normalising interceptor of the same instance.
 */
export function installAuthHandling(instance: AxiosInstance): void {
  instance.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.set?.('Authorization', `Bearer ${token}`);
    }
    return config;
  });

  instance.interceptors.response.use(undefined, async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => config?.url?.includes(path));
    if (
      error.response?.status === 401 &&
      config &&
      !config._retriedAfterRefresh &&
      !isAuthEndpoint
    ) {
      config._retriedAfterRefresh = true;
      const token = await refreshAccessToken();
      if (token) {
        config.headers.set?.('Authorization', `Bearer ${token}`);
        return instance.request(config);
      }
    }
    throw error;
  });
}
