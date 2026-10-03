import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Menu, Moon, Search, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserMenu } from '@/components/layout/UserMenu';
import { NotificationsMenu } from '@/features/notifications';
import { SegmentoBadge } from '@/features/segmento';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useBreadcrumbs } from '@/hooks/useBreadcrumbs';
import { api } from '@/lib/api';
import { AuthContext } from '@/features/auth/context/AuthContext';
import { applyTheme } from '@/features/auth/preferences';
import type { User } from '@/features/auth/types';
import { cn } from '@/lib/utils';

interface HeaderProps {
  onToggleSidebar?: () => void;
  onLogout?: () => void;
  userName?: string;
  userRole?: string;
  userEmail?: string;
}

interface HealthStatus {
  status: string;
  version?: string;
  environment?: string;
}

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

/** Live API status from the (cheap, public) /health endpoint, polled every minute. */
function ApiStatusPill() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<HealthStatus>('/health'),
    refetchInterval: 60_000,
    retry: false,
  });
  const online = !isError && data?.status === 'ok';
  const label = isLoading ? 'Conectando…' : online ? 'API en línea' : 'API sin conexión';

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={cn(
            'hidden items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium lg:flex',
            online
              ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
              : isLoading
                ? 'border-border bg-muted/50 text-muted-foreground'
                : 'border-rose-500/25 bg-rose-500/10 text-rose-700 dark:text-rose-400',
          )}
          role="status"
        >
          <span className="relative flex h-2 w-2">
            {online && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            )}
            <span
              className={cn(
                'relative inline-flex h-2 w-2 rounded-full',
                online ? 'bg-emerald-500' : isLoading ? 'bg-muted-foreground/50' : 'bg-rose-500',
              )}
            />
          </span>
          {label}
        </div>
      </TooltipTrigger>
      <TooltipContent>
        {online
          ? `Market Insight API v${data?.version ?? '—'} · ${data?.environment ?? ''}`
          : 'No se pudo contactar el backend'}
      </TooltipContent>
    </Tooltip>
  );
}

export function Header({
  onToggleSidebar,
  onLogout,
  userName = 'Arturo S.',
  userRole = 'Analista',
  userEmail,
}: HeaderProps) {
  const navigate = useNavigate();
  const breadcrumbs = useBreadcrumbs();
  const sectionTitle = breadcrumbs[0]?.label ?? 'Dashboard';
  const searchRef = React.useRef<HTMLInputElement>(null);
  const [search, setSearch] = React.useState('');

  const [isDark, setIsDark] = React.useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  const auth = React.useContext(AuthContext);
  const toggleTheme = () => {
    const theme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
    applyTheme(theme);
    setIsDark(theme === 'dark');
    // Persist to the account so it follows the user (Configuración → Apariencia).
    if (auth?.user) {
      void api
        .put<User>('/auth/me/preferences', { ...auth.user.preferences, theme })
        .then(auth.setUser)
        .catch(() => undefined);
    }
  };

  // Ctrl/⌘ + K focuses the global search from anywhere.
  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const q = search.trim();
    if (!q) return;
    navigate(`/search?q=${encodeURIComponent(q)}`);
    searchRef.current?.blur();
  };

  return (
    <TooltipProvider delayDuration={200}>
      <header className="sticky top-0 z-40 w-full border-b border-border/70 bg-background/80 shadow-[0_1px_0_0_rgba(0,0,0,0.02)] backdrop-blur-xl supports-[backdrop-filter]:bg-background/65">
        <div className="flex h-16 items-center gap-3 px-4 md:px-6">
          {/* Left: sidebar toggle + current section */}
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleSidebar}
              className="h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground"
              aria-label="Alternar barra lateral"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="hidden h-6 w-px bg-border/80 md:block" />
            <div className="hidden min-w-0 md:block">
              <p className="truncate text-sm font-semibold leading-tight text-foreground">
                {sectionTitle}
              </p>
              <p className="truncate text-[11px] leading-tight text-muted-foreground">
                Inteligencia de compras públicas
              </p>
            </div>
          </div>

          {/* Center: global search */}
          <form
            onSubmit={submitSearch}
            className="relative mx-auto hidden w-full max-w-md flex-1 sm:block"
            role="search"
          >
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              ref={searchRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar licitación, proveedor, RUT o código…"
              aria-label="Búsqueda global"
              className="h-9 w-full rounded-lg border border-border/70 bg-muted/40 pl-9 pr-16 text-xs text-foreground transition-colors placeholder:text-muted-foreground hover:bg-muted/60 focus:border-primary/50 focus:bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <kbd className="pointer-events-none absolute right-2 top-1/2 hidden h-5 -translate-y-1/2 select-none items-center gap-0.5 rounded border border-border/80 bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground md:flex">
              {isMac ? '⌘' : 'Ctrl'} K
            </kbd>
          </form>

          {/* Right: context + actions */}
          <div className="ml-auto flex shrink-0 items-center gap-1.5 md:gap-2">
            <SegmentoBadge />
            <ApiStatusPill />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  className="h-9 w-9 text-muted-foreground hover:text-foreground"
                  aria-label="Cambiar tema claro/oscuro"
                >
                  {isDark ? (
                    <Sun className="h-4 w-4 text-amber-400" />
                  ) : (
                    <Moon className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{isDark ? 'Modo claro' : 'Modo oscuro'}</TooltipContent>
            </Tooltip>

            <NotificationsMenu />

            <div className="mx-1 hidden h-6 w-px bg-border/80 sm:block" />

            <UserMenu
              userName={userName}
              userRole={userRole}
              userEmail={userEmail}
              onLogout={onLogout}
            />
          </div>
        </div>
      </header>
    </TooltipProvider>
  );
}
