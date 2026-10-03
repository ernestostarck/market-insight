import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/features/auth/hooks/useAuth';
import type { User, UserPreferences, UserRole } from '@/features/auth/types';
import type { OffsetPage } from '@/types';

export interface SessionInfo {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  current: boolean;
}

export interface AuditEvent {
  id: number;
  created_at: string;
  event: string;
  success: boolean;
  actor_email: string | null;
  user_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  detail: Record<string, unknown>;
}

export interface AdminUser extends User {
  failed_login_attempts: number;
  locked_until: string | null;
}

export const EVENT_LABELS: Record<string, string> = {
  login_success: 'Inicio de sesión',
  login_failed: 'Intento de inicio fallido',
  login_blocked_locked: 'Intento con cuenta bloqueada',
  account_locked: 'Cuenta bloqueada',
  mfa_challenge_failed: 'Código MFA incorrecto',
  mfa_enabled: 'MFA activado',
  mfa_disabled: 'MFA desactivado',
  refresh_token_reuse_detected: 'Posible robo de sesión detectado',
  logout: 'Cierre de sesión',
  logout_all: 'Cierre de todas las sesiones',
  session_revoked: 'Sesión revocada',
  password_changed: 'Contraseña cambiada',
  password_change_failed: 'Cambio de contraseña rechazado',
  profile_updated: 'Perfil actualizado',
  user_created: 'Usuario creado',
  user_updated: 'Usuario modificado',
  firewall_block: 'Bloqueo del firewall',
  ip_banned: 'IP bloqueada temporalmente',
  auth_rate_limited: 'Exceso de intentos de acceso',
};

/** Keeps the auth context's cached profile in sync after a mutation. */
function useSyncUser() {
  const { setUser } = useAuth();
  return (user: User) => setUser(user);
}

export function useUpdateProfile() {
  const syncUser = useSyncUser();
  return useMutation({
    mutationFn: (payload: { full_name?: string | null; job_title?: string | null }) =>
      api.patch<User>('/auth/me', payload),
    onSuccess: syncUser,
  });
}

export function useUpdatePreferences() {
  const syncUser = useSyncUser();
  return useMutation({
    mutationFn: (preferences: UserPreferences) =>
      api.put<User>('/auth/me/preferences', preferences),
    onSuccess: syncUser,
  });
}

export function useChangePassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { current_password: string; new_password: string }) =>
      api.post<void>('/auth/me/password', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['account'] }),
  });
}

export function useMfaSetup() {
  return useMutation({
    mutationFn: () => api.post<{ secret: string; otpauth_uri: string }>('/auth/me/mfa/setup'),
  });
}

export function useMfaEnable() {
  const syncUser = useSyncUser();
  return useMutation({
    mutationFn: (code: string) => api.post<User>('/auth/me/mfa/enable', { code }),
    onSuccess: syncUser,
  });
}

export function useMfaDisable() {
  const syncUser = useSyncUser();
  return useMutation({
    mutationFn: (payload: { password: string; code: string }) =>
      api.post<User>('/auth/me/mfa/disable', payload),
    onSuccess: syncUser,
  });
}

export function useSessions() {
  return useQuery({
    queryKey: ['account', 'sessions'],
    queryFn: () => api.get<SessionInfo[]>('/auth/me/sessions'),
  });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => api.delete<void>(`/auth/me/sessions/${sessionId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['account'] }),
  });
}

export function useLogoutEverywhere() {
  return useMutation({ mutationFn: () => api.post<void>('/auth/logout-all') });
}

export function useMyActivity() {
  return useQuery({
    queryKey: ['account', 'activity'],
    queryFn: () => api.get<AuditEvent[]>('/auth/me/activity'),
  });
}

// -- Administration ------------------------------------------------------------------

export function useAdminUsers(enabled: boolean) {
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => api.get<AdminUser[]>('/admin/users'),
    enabled,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      email: string;
      password: string;
      full_name?: string;
      job_title?: string;
      role: UserRole;
    }) => api.post<AdminUser>('/admin/users', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin'] }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: string;
      role?: UserRole;
      is_active?: boolean;
      unlock?: boolean;
      reset_mfa?: boolean;
      revoke_sessions?: boolean;
    }) => api.patch<AdminUser>(`/admin/users/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin'] }),
  });
}

export function useAuditLog(
  params: { limit: number; offset: number; event?: string; success?: boolean; q?: string },
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['admin', 'audit', params],
    queryFn: () => api.get<OffsetPage<AuditEvent>>('/admin/audit', { params }),
    placeholderData: keepPreviousData,
    enabled,
  });
}
