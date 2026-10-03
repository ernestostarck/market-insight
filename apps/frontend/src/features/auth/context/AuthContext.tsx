import React, { createContext, useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { clearSession, getAccessToken, refreshAccessToken, setAccessToken } from '@/lib/session';
import { applyPreferences } from '@/features/auth/preferences';
import type { LoginCredentials, LoginResponse, LoginResult, User } from '@/features/auth/types';
import { DEMO_MODE, DEMO_TOKEN, DEMO_USER } from '@/lib/demo';

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Password step. Resolves to `mfa_required` when the account has MFA enabled. */
  login: (credentials: LoginCredentials) => Promise<LoginResult>;
  /** Second step for MFA accounts. */
  verifyMfa: (mfaToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  /** Replace the cached profile after a profile/preferences update. */
  setUser: (user: User) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    DEMO_MODE ? DEMO_TOKEN : getAccessToken(),
  );
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const setUser = useCallback((next: User) => {
    setUserState(next);
    applyPreferences(next.preferences);
  }, []);

  const resetLocalSession = useCallback(() => {
    clearSession();
    setToken(null);
    setUserState(null);
  }, []);

  const loadProfile = useCallback(async () => {
    const profile = await api.get<User>('/auth/me');
    setUserState(profile);
    applyPreferences(profile.preferences, { onLogin: true });
  }, []);

  const checkAuth = useCallback(async () => {
    if (DEMO_MODE) {
      setToken(DEMO_TOKEN);
      setUserState(DEMO_USER);
      applyPreferences(DEMO_USER.preferences, { onLogin: true });
      setIsLoading(false);
      return;
    }
    try {
      // No access token (or an expired one): the httpOnly refresh cookie may still
      // hold a live session, e.g. after closing and reopening the tab.
      if (!getAccessToken() && !(await refreshAccessToken())) {
        resetLocalSession();
        return;
      }
      setToken(getAccessToken());
      await loadProfile();
    } catch {
      resetLocalSession();
    } finally {
      setIsLoading(false);
    }
  }, [loadProfile, resetLocalSession]);

  useEffect(() => {
    void checkAuth();
    const handleUnauthorized = () => resetLocalSession();
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [checkAuth, resetLocalSession]);

  const startSession = useCallback(
    async (response: LoginResponse) => {
      if (!response.access_token) throw new Error('Respuesta de autenticación inválida.');
      setAccessToken(response.access_token, response.expires_in);
      setToken(response.access_token);
      await loadProfile();
    },
    [loadProfile],
  );

  const login = async (credentials: LoginCredentials): Promise<LoginResult> => {
    setIsLoading(true);
    try {
      // FastAPI OAuth2PasswordRequestForm expects a form-urlencoded body.
      const form = new URLSearchParams();
      form.append('username', credentials.email);
      form.append('password', credentials.password);
      const response = await api.post<LoginResponse>('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        withCredentials: true,
      });
      if (response.mfa_required && response.mfa_token) {
        return { status: 'mfa_required', mfaToken: response.mfa_token };
      }
      await startSession(response);
      return { status: 'authenticated' };
    } catch (err) {
      resetLocalSession();
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const verifyMfa = async (mfaToken: string, code: string): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await api.post<LoginResponse>(
        '/auth/mfa/verify',
        { mfa_token: mfaToken, code: code.replace(/\s/g, '') },
        { withCredentials: true },
      );
      await startSession(response);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = useCallback(async () => {
    if (DEMO_MODE) return;
    try {
      // Revokes the session server-side and clears the refresh cookie.
      await api.post('/auth/logout', null, { withCredentials: true });
    } catch {
      // Even if the server is unreachable, drop the local session.
    }
    resetLocalSession();
  }, [resetLocalSession]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        verifyMfa,
        logout,
        checkAuth,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
