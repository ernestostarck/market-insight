import React, { useEffect, useMemo, useState } from 'react';
import {
  Laptop,
  Loader2,
  Lock,
  Moon,
  RotateCcw,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  UserPlus,
  Users,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { applyPreferences } from '@/features/auth/preferences';
import { ROLE_LABELS, type UserPreferences, type UserRole } from '@/features/auth/types';
import { FALLBACK_TAXONOMIA } from '@/features/taxonomia';
import {
  useAdminUsers,
  useCreateUser,
  useUpdatePreferences,
  useUpdateUser,
  type AdminUser,
} from '@/features/account/api';
import { formatDateTime } from '@/lib/formatters';
import { cn } from '@/lib/utils';

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'system',
  default_page_size: 10,
  landing_page: '/dashboard',
  default_segmento: null,
  compact_tables: false,
};

const LANDING_OPTIONS: { value: UserPreferences['landing_page']; label: string }[] = [
  { value: '/dashboard', label: 'Dashboard' },
  { value: '/mercado', label: 'Mercado' },
  { value: '/licitaciones', label: 'Licitaciones' },
  { value: '/proveedores', label: 'Proveedores' },
  { value: '/rubros', label: 'Rubros' },
];

const selectClass =
  'h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40';

type Tab = 'preferences' | 'users' | 'security';

function errorMessage(err: unknown): string {
  const e = err as { message?: string; detail?: unknown };
  const detail = e?.detail as { password?: string[] } | undefined;
  if (detail && !Array.isArray(detail) && Array.isArray(detail.password))
    return detail.password.join(' ');
  return e?.message || 'No se pudo completar la operación.';
}

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-3">
      <span>
        <span className="block text-sm font-medium text-foreground">{label}</span>
        <span className="block text-xs text-muted-foreground">{description}</span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40',
          checked ? 'bg-primary' : 'bg-muted-foreground/30',
        )}
      >
        <span
          className={cn(
            'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0.5',
          )}
        />
      </button>
    </label>
  );
}

// -- Preferences ---------------------------------------------------------------------------

function PreferencesTab() {
  const { user } = useAuth();
  const save = useUpdatePreferences();
  const saved = useMemo(
    () => ({ ...DEFAULT_PREFERENCES, ...user?.preferences }),
    [user?.preferences],
  );
  const [draft, setDraft] = useState<UserPreferences>(saved);
  useEffect(() => setDraft(saved), [saved]);

  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const set = <K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) => {
    const next = { ...draft, [key]: value };
    setDraft(next);
    // Live preview of visual settings; persisted only on "Guardar".
    if (key === 'theme' || key === 'compact_tables') applyPreferences(next);
  };

  const segmentoOptions = useMemo(
    () =>
      FALLBACK_TAXONOMIA.categories.map((category) => ({
        category,
        concepts: category.subcategories.flatMap((s) => s.concepts),
      })),
    [],
  );

  return (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(draft);
      }}
    >
      <Card className="rounded-xl border border-border/80 p-6 shadow-sm">
        <h2 className="text-sm font-bold text-foreground">Apariencia</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Se guarda en tu cuenta y te sigue en cualquier navegador.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {(
            [
              { value: 'light', label: 'Claro', icon: Sun },
              { value: 'dark', label: 'Oscuro', icon: Moon },
              { value: 'system', label: 'Según el sistema', icon: Laptop },
            ] as const
          ).map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => set('theme', value)}
              aria-pressed={draft.theme === value}
              className={cn(
                'flex items-center gap-3 rounded-lg border p-4 text-left text-sm transition-colors',
                draft.theme === value
                  ? 'border-primary bg-primary/5 ring-1 ring-primary/40'
                  : 'border-border hover:bg-muted/40',
              )}
            >
              <Icon className="h-4 w-4 text-primary" />
              <span className="font-medium text-foreground">{label}</span>
            </button>
          ))}
        </div>
        <div className="mt-2 divide-y divide-border/60">
          <Toggle
            checked={draft.compact_tables}
            onChange={(v) => set('compact_tables', v)}
            label="Tablas compactas"
            description="Reduce el espacio entre filas para ver más registros a la vez."
          />
        </div>
      </Card>

      <Card className="rounded-xl border border-border/80 p-6 shadow-sm">
        <h2 className="text-sm font-bold text-foreground">Navegación y datos</h2>
        <div className="mt-4 grid gap-5 md:grid-cols-3">
          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-foreground">Página de inicio</span>
            <select
              className={selectClass}
              value={draft.landing_page}
              onChange={(e) =>
                set('landing_page', e.target.value as UserPreferences['landing_page'])
              }
            >
              {LANDING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <span className="block text-[11px] text-muted-foreground">
              A dónde te lleva el sistema al iniciar sesión.
            </span>
          </label>
          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-foreground">Filas por página</span>
            <select
              className={selectClass}
              value={draft.default_page_size}
              onChange={(e) =>
                set(
                  'default_page_size',
                  Number(e.target.value) as UserPreferences['default_page_size'],
                )
              }
            >
              {[10, 25, 50, 100].map((n) => (
                <option key={n} value={n}>
                  Top {n}
                </option>
              ))}
            </select>
            <span className="block text-[11px] text-muted-foreground">
              Valor inicial en Proveedores, Organismos, Categorías, Licitaciones y Adjudicaciones.
            </span>
          </label>
          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-foreground">Rubro por defecto</span>
            <select
              className={selectClass}
              value={draft.default_segmento ?? ''}
              onChange={(e) => set('default_segmento', e.target.value || null)}
            >
              <option value="">Ninguno (geriatría y discapacidad)</option>
              {segmentoOptions.map(({ category, concepts }) => (
                <optgroup key={category.code} label={category.name}>
                  <option value={`cat:${category.code}`}>{category.name} (rubro completo)</option>
                  {concepts.map((c) => (
                    <option key={c.code} value={`concept:${c.code}`}>
                      {c.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            <span className="block text-[11px] text-muted-foreground">
              Se activa automáticamente al iniciar sesión.
            </span>
          </label>
        </div>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" disabled={!dirty} isLoading={save.isPending}>
          Guardar preferencias
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="gap-1.5"
          onClick={() => {
            setDraft(DEFAULT_PREFERENCES);
            applyPreferences(DEFAULT_PREFERENCES);
          }}
        >
          <RotateCcw className="h-3.5 w-3.5" /> Restablecer valores
        </Button>
        {dirty && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Tienes cambios sin guardar.
          </span>
        )}
        {save.isSuccess && !dirty && (
          <span className="text-xs text-emerald-600 dark:text-emerald-400">
            Preferencias guardadas.
          </span>
        )}
        {save.isError && (
          <span className="text-xs text-destructive">{errorMessage(save.error)}</span>
        )}
      </div>
    </form>
  );
}

// -- Users (admin) -----------------------------------------------------------------------------

function CreateUserForm() {
  const create = useCreateUser();
  const [form, setForm] = useState({
    email: '',
    full_name: '',
    job_title: '',
    password: '',
    role: 'analyst' as UserRole,
  });
  const update = (key: keyof typeof form, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  return (
    <Card className="rounded-xl border border-border/80 p-6 shadow-sm">
      <h2 className="flex items-center gap-2 text-sm font-bold text-foreground">
        <UserPlus className="h-4 w-4 text-primary" /> Crear cuenta
      </h2>
      <p className="mt-0.5 text-xs text-muted-foreground">
        El registro público está cerrado. Comparte la contraseña inicial por un canal seguro y pide
        que la cambie al entrar.
      </p>
      <form
        className="mt-4 grid gap-3 md:grid-cols-5"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            {
              ...form,
              full_name: form.full_name || undefined,
              job_title: form.job_title || undefined,
            },
            {
              onSuccess: () =>
                setForm({ email: '', full_name: '', job_title: '', password: '', role: 'analyst' }),
            },
          );
        }}
      >
        <Input
          type="email"
          required
          placeholder="correo@empresa.cl"
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
        />
        <Input
          placeholder="Nombre completo"
          value={form.full_name}
          onChange={(e) => update('full_name', e.target.value)}
        />
        <Input
          type="password"
          required
          autoComplete="new-password"
          placeholder="Contraseña inicial"
          value={form.password}
          onChange={(e) => update('password', e.target.value)}
        />
        <select
          className={selectClass}
          value={form.role}
          onChange={(e) => update('role', e.target.value)}
        >
          <option value="analyst">Analista</option>
          <option value="admin">Administrador</option>
        </select>
        <Button type="submit" size="sm" className="h-10" isLoading={create.isPending}>
          Crear
        </Button>
      </form>
      {create.isError && (
        <p className="mt-3 text-xs text-destructive">{errorMessage(create.error)}</p>
      )}
      {create.isSuccess && (
        <p className="mt-3 text-xs text-emerald-600 dark:text-emerald-400">Cuenta creada.</p>
      )}
    </Card>
  );
}

function UserRow({ account, isSelf }: { account: AdminUser; isSelf: boolean }) {
  const update = useUpdateUser();
  const locked = account.locked_until && new Date(account.locked_until) > new Date();
  const act = (payload: Parameters<typeof update.mutate>[0]) => update.mutate(payload);

  return (
    <tr className="align-top">
      <td className="py-3 pr-4">
        <p className="font-semibold text-foreground">{account.full_name || account.email}</p>
        <p className="text-muted-foreground">{account.email}</p>
      </td>
      <td className="py-3 pr-4">
        <select
          className="h-8 rounded-md border border-border bg-background px-2 text-xs"
          value={account.role}
          disabled={isSelf || update.isPending}
          onChange={(e) => act({ id: account.id, role: e.target.value as UserRole })}
        >
          <option value="analyst">{ROLE_LABELS.analyst}</option>
          <option value="admin">{ROLE_LABELS.admin}</option>
        </select>
      </td>
      <td className="py-3 pr-4">
        <div className="flex flex-wrap gap-1">
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-[10px] font-bold',
              account.is_active
                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                : 'bg-muted text-muted-foreground',
            )}
          >
            {account.is_active ? 'Activa' : 'Desactivada'}
          </span>
          {locked && (
            <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
              Bloqueada
            </span>
          )}
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-[10px] font-bold',
              account.mfa_enabled
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
                : 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
            )}
          >
            {account.mfa_enabled ? 'MFA' : 'Sin MFA'}
          </span>
        </div>
      </td>
      <td className="py-3 pr-4 text-muted-foreground">
        {account.last_login_at ? formatDateTime(account.last_login_at) : 'Nunca'}
      </td>
      <td className="py-3">
        <div className="flex flex-wrap justify-end gap-1">
          {locked && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-[11px]"
              onClick={() => act({ id: account.id, unlock: true })}
            >
              Desbloquear
            </Button>
          )}
          {account.mfa_enabled && !isSelf && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-[11px]"
              onClick={() => act({ id: account.id, reset_mfa: true })}
            >
              Restablecer MFA
            </Button>
          )}
          {!isSelf && (
            <>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-[11px]"
                onClick={() => act({ id: account.id, revoke_sessions: true })}
              >
                Cerrar sesiones
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-[11px] text-destructive"
                onClick={() => act({ id: account.id, is_active: !account.is_active })}
              >
                {account.is_active ? 'Desactivar' : 'Reactivar'}
              </Button>
            </>
          )}
        </div>
        {update.isError && (
          <p className="mt-1 text-right text-[11px] text-destructive">
            {errorMessage(update.error)}
          </p>
        )}
      </td>
    </tr>
  );
}

function UsersTab() {
  const { user } = useAuth();
  const { data: users = [], isLoading } = useAdminUsers(true);
  return (
    <div className="space-y-6">
      <CreateUserForm />
      <Card className="overflow-hidden rounded-xl border border-border/80 shadow-sm">
        <div className="border-b border-border/80 bg-muted/20 px-5 py-3.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          {users.length} cuentas
        </div>
        {isLoading ? (
          <div className="p-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="overflow-x-auto px-5">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="py-3 pr-4">Usuario</th>
                  <th className="py-3 pr-4">Rol</th>
                  <th className="py-3 pr-4">Estado</th>
                  <th className="py-3 pr-4">Último acceso</th>
                  <th className="py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {users.map((account) => (
                  <UserRow key={account.id} account={account} isSelf={account.id === user?.id} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// -- Security policy (read-only summary of what the backend enforces) ---------------------

const SECURITY_CONTROLS: { title: string; items: string[] }[] = [
  {
    title: 'Identidad y acceso',
    items: [
      'Registro público deshabilitado; cuentas creadas solo por administradores.',
      'Contraseñas con Argon2id, mínimo 12 caracteres con mayúsculas, minúsculas, números y símbolos.',
      'Bloqueo de cuenta tras 5 intentos fallidos, con espera exponencial (15 min → 24 h).',
      'Verificación en dos pasos (TOTP) por usuario; secretos cifrados en la base de datos.',
      'Roles con mínimo privilegio: Analista y Administrador.',
    ],
  },
  {
    title: 'Sesiones',
    items: [
      'Token de acceso de 15 minutos; sesión máxima de 8 horas.',
      'Refresh token en cookie httpOnly + SameSite=Strict, inaccesible desde JavaScript.',
      'Rotación del refresh token en cada uso; reutilizar uno antiguo revoca todas las sesiones (detección de robo).',
      'Cerrar sesión, cambiar contraseña o desactivar una cuenta invalida sus tokens en el acto.',
    ],
  },
  {
    title: 'Firewall y red',
    items: [
      'WAF de aplicación: bloquea inyección SQL, XSS, path traversal, Log4Shell, SSRF y escáneres conocidos.',
      'Baneo temporal automático de IPs con actividad hostil (20 incidentes en 10 min → 15 min).',
      'Límite de intentos de autenticación por IP y límite global de solicitudes.',
      'Listas de IPs permitidas/denegadas, validación de Host y tamaño máximo de solicitud.',
      'Cabeceras de seguridad: CSP, HSTS, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy.',
    ],
  },
  {
    title: 'Datos',
    items: [
      'El usuario de la aplicación no es dueño del esquema: no puede alterar tablas.',
      'Documentación interactiva de la API deshabilitada fuera de desarrollo.',
      'La aplicación se niega a arrancar en producción con claves débiles o DEBUG activo.',
    ],
  },
];

function SecurityTab() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {SECURITY_CONTROLS.map((group) => (
        <Card key={group.title} className="rounded-xl border border-border/80 p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-foreground">
            <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> {group.title}
          </h2>
          <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
            {group.items.map((item) => (
              <li key={item} className="flex gap-2">
                <Lock className="mt-0.5 h-3 w-3 shrink-0 text-primary" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </div>
  );
}

// -- Page --------------------------------------------------------------------------------

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [tab, setTab] = useState<Tab>('preferences');

  const tabs: {
    id: Tab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    admin?: boolean;
  }[] = [
    { id: 'preferences', label: 'Preferencias', icon: SlidersHorizontal },
    { id: 'users', label: 'Usuarios', icon: Users, admin: true },
    { id: 'security', label: 'Seguridad', icon: ShieldCheck },
  ];

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Configuración
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ajustes de tu cuenta
          {isAdmin ? ' y administración de usuarios' : ''}.
        </p>
        <div className="mt-5 flex flex-wrap gap-1 border-b border-border/80" role="tablist">
          {tabs
            .filter((t) => !t.admin || isAdmin)
            .map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                role="tab"
                aria-selected={tab === id}
                onClick={() => setTab(id)}
                className={cn(
                  '-mb-px flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors',
                  tab === id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="h-4 w-4" /> {label}
              </button>
            ))}
        </div>
      </div>

      {tab === 'preferences' && <PreferencesTab />}
      {tab === 'users' && isAdmin && <UsersTab />}
      {tab === 'security' && <SecurityTab />}
    </div>
  );
};
