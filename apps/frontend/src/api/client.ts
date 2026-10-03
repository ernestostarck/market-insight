import axios from 'axios';

import { clearSession, getAccessToken, installAuthHandling, setAccessToken } from '@/lib/session';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30000,
});

export const getToken = getAccessToken;
export const setToken = (token: string): void => setAccessToken(token);
export const clearToken = clearSession;

installAuthHandling(apiClient);

function generateRandomHex(bytes: number): string {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const arr = new Uint8Array(bytes);
    crypto.getRandomValues(arr);
    return Array.from(arr, (b) => b.toString(16).padStart(2, '0')).join('');
  }
  return Array.from({ length: bytes * 2 }, () => Math.floor(Math.random() * 16).toString(16)).join(
    '',
  );
}

apiClient.interceptors.request.use((config) => {
  // OpenTelemetry W3C distributed trace propagation (Fase 8.13)
  const requestId = `req_${generateRandomHex(8)}`;
  config.headers['X-Request-ID'] = requestId;

  const traceId = generateRandomHex(16);
  const spanId = generateRandomHex(8);
  config.headers['traceparent'] = `00-${traceId}-${spanId}-01`;

  return config;
});

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams();
  body.set('username', email);
  body.set('password', password);

  const response = await apiClient.post<{ access_token: string; token_type: string }>(
    '/auth/login',
    body,
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
  );
  setToken(response.data.access_token);
  return response.data.access_token;
}
