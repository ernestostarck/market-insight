export type UserRole = 'admin' | 'analyst';
export type ThemePreference = 'light' | 'dark' | 'system';

export interface UserPreferences {
  theme: ThemePreference;
  default_page_size: 10 | 25 | 50 | 100;
  landing_page: '/dashboard' | '/mercado' | '/licitaciones' | '/proveedores' | '/rubros';
  default_segmento: string | null;
  compact_tables: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  job_title: string | null;
  role: UserRole;
  is_active: boolean;
  mfa_enabled: boolean;
  preferences: UserPreferences;
  created_at: string;
  last_login_at: string | null;
  last_login_ip: string | null;
  password_changed_at: string | null;
}

export interface LoginResponse {
  access_token: string | null;
  token_type: string;
  expires_in: number | null;
  mfa_required: boolean;
  mfa_token: string | null;
}

/** @deprecated kept for older call sites; the login endpoint returns LoginResponse. */
export type TokenResponse = LoginResponse;

export interface LoginCredentials {
  email: string;
  password: string;
}

export type LoginResult =
  { status: 'authenticated' } | { status: 'mfa_required'; mfaToken: string };

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrador',
  analyst: 'Analista',
};
