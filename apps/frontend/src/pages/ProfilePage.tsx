import React, { useEffect, useMemo, useState } from 'react';
import QRCode from 'qrcode';
import {
  CheckCircle2,
  Circle,
  Copy,
  KeyRound,
  Laptop,
  Loader2,
  LogOut,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  UserRound,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { ROLE_LABELS } from '@/features/auth/types';
import {
  EVENT_LABELS,
  useChangePassword,
  useLogoutEverywhere,
  useMfaDisable,
  useMfaEnable,
  useMfaSetup,
  useMyActivity,
  useRevokeSession,
  useSessions,
  useUpdateProfile,
} from '@/features/account/api';
import { formatDateTime, formatRelativeTime } from '@/lib/formatters';
import { cn } from '@/lib/utils';

const PASSWORD_MIN_LENGTH = 12;

function errorMessage(err: unknown): string {
  const e = err as { message?: string; detail?: unknown };
  const detail = e?.detail as { password?: string[] } | undefined;
  if (detail && !Array.isArray(detail) && Array.isArray(detail.password))
    return detail.password.join(' ');
  return e?.message || 'No se pudo completar la operación.';
}

function Section({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="mb-5 flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-foreground">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
      </div>
      {children}
    </Card>
  );
}

function Feedback({ kind, children }: { kind: 'success' | 'error'; children: React.ReactNode }) {
  return (
    <p
      role={kind === 'error' ? 'alert' : 'status'}
      className={cn(
        'rounded-md border px-3 py-2 text-xs',
        kind === 'success'
          ? 'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
          : 'border-destructive/30 bg-destructive/10 text-destructive',
      )}
    >
      {children}
    </p>
  );
}

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-semibold text-foreground">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-muted-foreground">{hint}</span>}
    </label>
  );
}

// -- Personal information --------------------------------------------------------------

function PersonalInfo() {
  const { user } = useAuth();
  const update = useUpdateProfile();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [jobTitle, setJobTitle] = useState(user?.job_title ?? '');
  const dirty = fullName !== (user?.full_name ?? '') || jobTitle !== (user?.job_title ?? '');

  return (
    <Section
      icon={UserRound}
      title="Información personal"
      description="Cómo te ve el resto del equipo."
    >
      <form
        className="grid gap-4 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          update.mutate({ full_name: fullName.trim() || null, job_title: jobTitle.trim() || null });
        }}
      >
        <Field label="Nombre completo">
          <Input value={fullName} maxLength={120} onChange={(e) => setFullName(e.target.value)} />
        </Field>
        <Field label="Cargo">
          <Input value={jobTitle} maxLength={120} onChange={(e) => setJobTitle(e.target.value)} />
        </Field>
        <Field
          label="Correo"
          hint="El correo es tu usuario; solo un administrador puede cambiarlo."
        >
          <Input value={user?.email ?? ''} disabled readOnly />
        </Field>
        <Field label="Rol">
          <Input value={user ? ROLE_LABELS[user.role] : ''} disabled readOnly />
        </Field>
        <div className="flex items-center gap-3 sm:col-span-2">
          <Button type="submit" size="sm" disabled={!dirty} isLoading={update.isPending}>
            Guardar cambios
          </Button>
          {update.isSuccess && !dirty && <Feedback kind="success">Perfil actualizado.</Feedback>}
          {update.isError && <Feedback kind="error">{errorMessage(update.error)}</Feedback>}
        </div>
      </form>
    </Section>
  );
}

// -- Password ---------------------------------------------------------------------------

function passwordChecks(password: string, email: string | undefined, confirm: string) {
  const local = (email ?? '').split('@')[0].toLowerCase();
  return [
    {
      ok: password.length >= PASSWORD_MIN_LENGTH,
      label: `Al menos ${PASSWORD_MIN_LENGTH} caracteres`,
    },
    { ok: /[a-záéíóúñ]/.test(password), label: 'Una letra minúscula' },
    { ok: /[A-ZÁÉÍÓÚÑ]/.test(password), label: 'Una letra mayúscula' },
    { ok: /\d/.test(password), label: 'Un número' },
    { ok: /[^\w\s]|_/.test(password), label: 'Un símbolo (! # $ % …)' },
    {
      ok: password.length > 0 && !(local.length >= 4 && password.toLowerCase().includes(local)),
      label: 'No contiene tu usuario',
    },
    { ok: password.length > 0 && password === confirm, label: 'Ambas contraseñas coinciden' },
  ];
}

function PasswordSection() {
  const { user } = useAuth();
  const change = useChangePassword();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const checks = passwordChecks(next, user?.email, confirm);
  const valid = current.length > 0 && checks.every((c) => c.ok);

  return (
    <Section
      icon={KeyRound}
      title="Contraseña"
      description={
        user?.password_changed_at
          ? `Último cambio: ${formatDateTime(user.password_changed_at)}. Al cambiarla se cierran tus otras sesiones.`
          : 'Al cambiarla se cierran tus otras sesiones abiertas.'
      }
    >
      <form
        className="grid gap-4 lg:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          change.mutate(
            { current_password: current, new_password: next },
            {
              onSuccess: () => {
                setCurrent('');
                setNext('');
                setConfirm('');
              },
            },
          );
        }}
      >
        <div className="space-y-4">
          <Field label="Contraseña actual">
            <Input
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </Field>
          <Field label="Nueva contraseña">
            <Input
              type="password"
              autoComplete="new-password"
              value={next}
              maxLength={128}
              onChange={(e) => setNext(e.target.value)}
            />
          </Field>
          <Field label="Repite la nueva contraseña">
            <Input
              type="password"
              autoComplete="new-password"
              value={confirm}
              maxLength={128}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
        </div>
        <div className="space-y-4">
          <ul className="space-y-1.5 rounded-lg border border-border/80 bg-muted/30 p-4 text-xs">
            {checks.map((c) => (
              <li
                key={c.label}
                className={cn(
                  'flex items-center gap-2',
                  c.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground',
                )}
              >
                {c.ok ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  <Circle className="h-3.5 w-3.5" />
                )}
                {c.label}
              </li>
            ))}
          </ul>
          <Button type="submit" size="sm" disabled={!valid} isLoading={change.isPending}>
            Cambiar contraseña
          </Button>
          {change.isSuccess && (
            <Feedback kind="success">
              Contraseña actualizada. Tus otras sesiones se cerraron.
            </Feedback>
          )}
          {change.isError && <Feedback kind="error">{errorMessage(change.error)}</Feedback>}
        </div>
      </form>
    </Section>
  );
}

// -- MFA ---------------------------------------------------------------------------------

function MfaSection() {
  const { user } = useAuth();
  const setup = useMfaSetup();
  const enable = useMfaEnable();
  const disable = useMfaDisable();
  const [qr, setQr] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!setup.data) return;
    QRCode.toDataURL(setup.data.otpauth_uri, { margin: 1, width: 192, errorCorrectionLevel: 'M' })
      .then(setQr)
      .catch(() => setQr(null));
  }, [setup.data]);

  if (user?.mfa_enabled) {
    return (
      <Section
        icon={ShieldCheck}
        title="Verificación en dos pasos"
        description="Activada: además de tu contraseña se pide un código de tu teléfono."
      >
        <form
          className="grid gap-4 sm:grid-cols-3 sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            disable.mutate(
              { password, code },
              {
                onSuccess: () => {
                  setPassword('');
                  setCode('');
                },
              },
            );
          }}
        >
          <Field label="Contraseña">
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Field label="Código actual">
            <Input
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            />
          </Field>
          <Button
            type="submit"
            variant="outline"
            size="sm"
            disabled={!password || code.length !== 6}
            isLoading={disable.isPending}
            className="text-destructive"
          >
            Desactivar MFA
          </Button>
          {disable.isError && (
            <div className="sm:col-span-3">
              <Feedback kind="error">{errorMessage(disable.error)}</Feedback>
            </div>
          )}
        </form>
      </Section>
    );
  }

  return (
    <Section
      icon={ShieldAlert}
      title="Verificación en dos pasos"
      description="Recomendado: aunque alguien obtenga tu contraseña, no podrá entrar sin tu teléfono."
    >
      {!setup.data ? (
        <div className="space-y-3">
          <Button size="sm" onClick={() => setup.mutate()} isLoading={setup.isPending}>
            Activar verificación en dos pasos
          </Button>
          {setup.isError && <Feedback kind="error">{errorMessage(setup.error)}</Feedback>}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-[auto_1fr]">
          <div className="flex flex-col items-center gap-2">
            {qr ? (
              <img
                src={qr}
                alt="Código QR para la app de autenticación"
                className="h-48 w-48 rounded-lg border border-border bg-white p-2"
              />
            ) : (
              <div className="flex h-48 w-48 items-center justify-center rounded-lg border border-border">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>
          <ol className="space-y-4 text-xs text-foreground">
            <li>
              <span className="font-semibold">1.</span> Abre Google Authenticator, Microsoft
              Authenticator u otra app TOTP y escanea el código.
            </li>
            <li className="space-y-1.5">
              <span className="font-semibold">2.</span> ¿No puedes escanear? Ingresa esta clave
              manualmente:
              <div className="flex items-center gap-2">
                <code className="rounded bg-muted px-2 py-1 font-mono text-[11px] tracking-wider">
                  {setup.data.secret.match(/.{1,4}/g)?.join(' ')}
                </code>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 gap-1 text-[11px]"
                  onClick={() => {
                    void navigator.clipboard?.writeText(setup.data!.secret);
                    setCopied(true);
                  }}
                >
                  <Copy className="h-3 w-3" /> {copied ? 'Copiada' : 'Copiar'}
                </Button>
              </div>
            </li>
            <li>
              <span className="font-semibold">3.</span> Escribe el código de 6 dígitos que muestra
              la app:
              <form
                className="mt-2 flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  enable.mutate(code, { onSuccess: () => setCode('') });
                }}
              >
                <Input
                  autoFocus
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  className="w-32 text-center font-mono tracking-[0.3em]"
                  placeholder="000000"
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={code.length !== 6}
                  isLoading={enable.isPending}
                >
                  Confirmar
                </Button>
              </form>
              {enable.isError && (
                <div className="mt-2">
                  <Feedback kind="error">{errorMessage(enable.error)}</Feedback>
                </div>
              )}
            </li>
          </ol>
        </div>
      )}
    </Section>
  );
}

// -- Sessions & activity -------------------------------------------------------------------

function describeAgent(userAgent: string | null): { label: string; mobile: boolean } {
  const ua = userAgent ?? '';
  const mobile = /Mobile|Android|iPhone|iPad/i.test(ua);
  const browser = /Edg\//.test(ua)
    ? 'Edge'
    : /Chrome\//.test(ua)
      ? 'Chrome'
      : /Firefox\//.test(ua)
        ? 'Firefox'
        : /Safari\//.test(ua)
          ? 'Safari'
          : 'Navegador';
  const os = /Windows/.test(ua)
    ? 'Windows'
    : /Mac OS X/.test(ua)
      ? 'macOS'
      : /Android/.test(ua)
        ? 'Android'
        : /iPhone|iPad/.test(ua)
          ? 'iOS'
          : /Linux/.test(ua)
            ? 'Linux'
            : '';
  return { label: [browser, os].filter(Boolean).join(' · ') || 'Dispositivo desconocido', mobile };
}

function SessionsSection() {
  const { logout } = useAuth();
  const { data: sessions = [], isLoading } = useSessions();
  const revoke = useRevokeSession();
  const logoutAll = useLogoutEverywhere();

  return (
    <Section
      icon={Laptop}
      title="Sesiones activas"
      description="Dispositivos donde tu cuenta está abierta. Revoca cualquiera que no reconozcas."
    >
      {isLoading ? (
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      ) : (
        <ul className="divide-y divide-border/60">
          {sessions.map((s) => {
            const agent = describeAgent(s.user_agent);
            const Icon = agent.mobile ? Smartphone : Laptop;
            return (
              <li key={s.id} className="flex items-center justify-between gap-3 py-3">
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <div className="text-xs">
                    <p className="font-semibold text-foreground">
                      {agent.label}
                      {s.current && (
                        <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                          Esta sesión
                        </span>
                      )}
                    </p>
                    <p className="text-muted-foreground">
                      Activa{' '}
                      {formatRelativeTime(new Date(s.last_seen_at))} · expira{' '}
                      {formatDateTime(s.expires_at)}
                    </p>
                  </div>
                </div>
                {!s.current && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs text-destructive"
                    onClick={() => revoke.mutate(s.id)}
                    disabled={revoke.isPending}
                  >
                    Revocar
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <div className="mt-4 border-t border-border/60 pt-4">
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-destructive"
          isLoading={logoutAll.isPending}
          onClick={() => logoutAll.mutate(undefined, { onSettled: () => void logout() })}
        >
          <LogOut className="h-3.5 w-3.5" />
          Cerrar sesión en todos los dispositivos
        </Button>
      </div>
    </Section>
  );
}

function ActivitySection() {
  const { data: events = [], isLoading } = useMyActivity();
  return (
    <Section
      icon={ShieldCheck}
      title="Actividad de seguridad reciente"
      description="Registro inalterable de los últimos eventos de tu cuenta."
    >
      {isLoading ? (
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      ) : events.length === 0 ? (
        <p className="text-xs text-muted-foreground">Sin eventos todavía.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="pb-2 pr-4">Evento</th>
                <th className="pb-2 pr-4">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="py-2 pr-4">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1.5 font-medium',
                        e.success ? 'text-foreground' : 'text-destructive',
                      )}
                    >
                      <span
                        className={cn(
                          'h-1.5 w-1.5 rounded-full',
                          e.success ? 'bg-emerald-500' : 'bg-destructive',
                        )}
                      />
                      {EVENT_LABELS[e.event] ?? e.event}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-muted-foreground">
                    {formatDateTime(e.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

// -- Page --------------------------------------------------------------------------------

export const ProfilePage: React.FC = () => {
  const { user } = useAuth();
  const initials = useMemo(() => {
    const source = user?.full_name || user?.email || '?';
    return source
      .split(/[\s.@]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('');
  }, [user]);

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-5 rounded-xl border border-border/80 bg-card p-6 shadow-sm sm:flex-row sm:items-center">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-xl font-bold text-white shadow-md">
          {initials}
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {user.full_name || user.email}
            </h1>
            <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
              {ROLE_LABELS[user.role]}
            </span>
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                user.mfa_enabled
                  ? 'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                  : 'border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
              )}
            >
              {user.mfa_enabled ? (
                <ShieldCheck className="h-3 w-3" />
              ) : (
                <ShieldAlert className="h-3 w-3" />
              )}
              {user.mfa_enabled ? 'MFA activo' : 'MFA desactivado'}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {user.email}
            {user.job_title ? ` · ${user.job_title}` : ''}
          </p>
          <p className="text-xs text-muted-foreground">
            Miembro desde {formatDateTime(user.created_at)}
            {user.last_login_at &&
              ` · Último acceso ${formatDateTime(user.last_login_at)}`}
          </p>
        </div>
      </div>

      <PersonalInfo />
      <div className="grid gap-6 xl:grid-cols-2">
        <PasswordSection />
        <MfaSection />
      </div>
      <SessionsSection />
      <ActivitySection />
    </div>
  );
};
