import { FALLBACK_TAXONOMIA } from '@/features/taxonomia';
import { getSegmento, setSegmento } from '@/features/segmento/store';
import type { ThemePreference, UserPreferences } from '@/features/auth/types';

/**
 * Applies the signed-in user's saved settings (Configuración) to the running app.
 * Server-side storage (`PUT /auth/me/preferences`) makes them follow the user
 * across browsers and devices.
 */

let current: UserPreferences | null = null;
let systemThemeQuery: MediaQueryList | null = null;

function setDarkClass(dark: boolean): void {
  document.documentElement.classList.toggle('dark', dark);
}

function onSystemThemeChange(event: MediaQueryListEvent): void {
  if (current?.theme === 'system') setDarkClass(event.matches);
}

export function applyTheme(theme: ThemePreference): void {
  if (typeof window === 'undefined') return;
  systemThemeQuery ??= window.matchMedia?.('(prefers-color-scheme: dark)') ?? null;
  systemThemeQuery?.removeEventListener?.('change', onSystemThemeChange);
  if (theme === 'system') {
    setDarkClass(Boolean(systemThemeQuery?.matches));
    systemThemeQuery?.addEventListener?.('change', onSystemThemeChange);
  } else {
    setDarkClass(theme === 'dark');
  }
}

/** Human label for a `cat:<code>` / `concept:<code>` segment, from the taxonomy. */
export function segmentoLabel(code: string): { label: string; parentLabel?: string } | null {
  const [kind, value] = code.split(':');
  for (const category of FALLBACK_TAXONOMIA.categories) {
    if (kind === 'cat' && category.code === value) return { label: category.name };
    for (const sub of category.subcategories) {
      const concept = sub.concepts.find((c) => c.code === value);
      if (kind === 'concept' && concept) return { label: concept.name, parentLabel: category.name };
    }
  }
  return null;
}

export function applyPreferences(prefs: UserPreferences, { onLogin = false } = {}): void {
  current = prefs;
  if (typeof document === 'undefined') return;
  applyTheme(prefs.theme);
  document.documentElement.dataset.density = prefs.compact_tables ? 'compact' : 'comfortable';

  // The default rubro only seeds a fresh session; it never overrides a choice made since.
  if (onLogin && prefs.default_segmento && !getSegmento()) {
    const resolved = segmentoLabel(prefs.default_segmento);
    if (resolved) setSegmento({ code: prefs.default_segmento, ...resolved });
  }
}

/** Default rows per page for list views (falls back to 10 before login). */
export function preferredPageSize(): number {
  return current?.default_page_size ?? 10;
}

export function preferredLandingPage(): string {
  return current?.landing_page ?? '/dashboard';
}
