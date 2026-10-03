import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios, { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios';
import { clearSession, getAccessToken, installAuthHandling, setAccessToken } from '@/lib/session';

function unauthorized(config: InternalAxiosRequestConfig) {
  return Promise.reject(
    new AxiosError('401', 'ERR_BAD_REQUEST', config, null, {
      status: 401,
      statusText: 'Unauthorized',
      data: {},
      headers: {},
      config,
    }),
  );
}

describe('session refresh-and-retry', () => {
  beforeEach(() => {
    clearSession();
    vi.restoreAllMocks();
  });

  it('refreshes once on a 401 and retries the request with the new token', async () => {
    setAccessToken('expired-token');
    const refresh = vi
      .spyOn(axios, 'post')
      .mockResolvedValue({ data: { access_token: 'fresh-token', expires_in: 900 } });
    const seen: (string | undefined)[] = [];
    const adapter: AxiosAdapter = async (config) => {
      const auth = config.headers?.get?.('Authorization') as string | undefined;
      seen.push(auth);
      if (auth === 'Bearer expired-token') return unauthorized(config);
      return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config };
    };
    const client = axios.create({ adapter });
    installAuthHandling(client);

    const response = await client.get('/licitaciones');

    expect(response.data).toEqual({ ok: true });
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(refresh.mock.calls[0][0]).toContain('/auth/refresh');
    expect(seen).toEqual(['Bearer expired-token', 'Bearer fresh-token']);
    expect(getAccessToken()).toBe('fresh-token');
  });

  it('signals the end of the session when the refresh fails, without looping', async () => {
    setAccessToken('expired-token');
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh rejected'));
    const onUnauthorized = vi.fn();
    window.addEventListener('auth:unauthorized', onUnauthorized);
    let calls = 0;
    const client = axios.create({
      adapter: async (config) => {
        calls += 1;
        return unauthorized(config);
      },
    });
    installAuthHandling(client);

    await expect(client.get('/licitaciones')).rejects.toBeTruthy();

    expect(calls).toBe(1);
    expect(onUnauthorized).toHaveBeenCalled();
    expect(getAccessToken()).toBeNull();
    window.removeEventListener('auth:unauthorized', onUnauthorized);
  });

  it('never tries to refresh for the login endpoint itself', async () => {
    const refresh = vi.spyOn(axios, 'post');
    const client = axios.create({ adapter: async (config) => unauthorized(config) });
    installAuthHandling(client);

    await expect(client.post('/auth/login', 'x')).rejects.toBeTruthy();
    expect(refresh).not.toHaveBeenCalled();
  });
});
