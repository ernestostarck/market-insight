import * as React from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { Breadcrumbs, type BreadcrumbItem } from '@/components/layout/Breadcrumbs';
import { useBreadcrumbs } from '@/hooks/useBreadcrumbs';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { cn } from '@/lib/utils';
import { ROLE_LABELS } from '@/features/auth/types';

export interface AppLayoutProps {
  children: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  userName?: string;
  userRole?: string;
  onLogout?: () => void;
  activeNavId?: string;
  onSelectNav?: (id: string) => void;
}

export function AppLayout({
  children,
  breadcrumbs,
  userName,
  userRole,
  onLogout,
  activeNavId: _activeNavId,
  onSelectNav,
}: AppLayoutProps) {
  const [isCollapsed, setIsCollapsed] = React.useState<boolean>(false);
  const [isMobileOpen, setIsMobileOpen] = React.useState<boolean>(false);

  // Hook breadcrumbs fallback
  const autoBreadcrumbs = useBreadcrumbs();
  const effectiveBreadcrumbs = breadcrumbs || autoBreadcrumbs;

  // Auth context fallback
  let authContextUser: string | undefined;
  let authContextEmail: string | undefined;
  let authContextRole: string | undefined;
  let authLogout: (() => void) | undefined;
  try {
    const auth = useAuth();
    authContextUser = auth.user ? auth.user.full_name || auth.user.email.split('@')[0] : undefined;
    authContextEmail = auth.user?.email;
    authContextRole = auth.user ? ROLE_LABELS[auth.user.role] : undefined;
    authLogout = auth.logout;
  } catch {
    // Rendered outside AuthProvider (e.g. in standalone test)
  }

  const effectiveUserName = userName || authContextUser || 'Arturo S.';
  const effectiveUserRole = userRole || authContextRole || 'Analista';
  const effectiveLogout = onLogout || authLogout;

  const toggleSidebar = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setIsMobileOpen((prev) => !prev);
    } else {
      setIsCollapsed((prev) => !prev);
    }
  };

  return (
    <div className="flex min-h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar for Desktop & Mobile */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 transition-transform duration-300 ease-in-out md:relative md:flex',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        )}
      >
        <Sidebar
          isCollapsed={isCollapsed}
          onToggleCollapse={() => setIsCollapsed((prev) => !prev)}
          onSelectNav={(id) => {
            setIsMobileOpen(false);
            if (onSelectNav) onSelectNav(id);
          }}
        />
      </div>

      {/* Main Viewport Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Sticky Header */}
        <Header
          onToggleSidebar={toggleSidebar}
          onLogout={effectiveLogout}
          userName={effectiveUserName}
          userRole={effectiveUserRole}
          userEmail={authContextEmail}
        />

        {/* Scrollable Main Content Container */}
        <main className="flex flex-1 flex-col overflow-y-auto">
          <div className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 py-6 md:px-8">
            {/* Breadcrumb Trail */}
            {effectiveBreadcrumbs && effectiveBreadcrumbs.length > 0 && (
              <Breadcrumbs items={effectiveBreadcrumbs} className="mb-2" />
            )}

            {/* Dynamic Page Content */}
            {children}
          </div>

          <Footer />
        </main>
      </div>
    </div>
  );
}
