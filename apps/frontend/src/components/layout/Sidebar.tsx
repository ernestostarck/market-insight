import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Award,
  BarChart3,
  Boxes,
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  HelpCircle,
  LayoutDashboard,
  Search,
  ShoppingCart,
  Sparkles,
  Tags,
  TrendingUp,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  badge?: string;
  badgeVariant?: 'default' | 'accent' | 'secondary';
}

export const NAVIGATION_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { id: 'mercado', label: 'Mercado', icon: TrendingUp, href: '/mercado' },
  {
    id: 'licitaciones',
    label: 'Licitaciones',
    icon: FileText,
    href: '/licitaciones',
    badge: '128',
  },
  { id: 'proveedores', label: 'Proveedores', icon: Users, href: '/proveedores' },
  { id: 'organismos', label: 'Organismos', icon: Building2, href: '/organismos' },
  { id: 'categorias', label: 'Categorías', icon: Tags, href: '/categorias' },
  { id: 'rubros', label: 'Rubros', icon: Boxes, href: '/rubros' },
  { id: 'adjudicaciones', label: 'Adjudicaciones', icon: Award, href: '/adjudicaciones' },
  { id: 'ordenes-compra', label: 'Órdenes de Compra', icon: ShoppingCart, href: '/ordenes-compra' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, href: '/analytics' },
  { id: 'search', label: 'Búsqueda', icon: Search, href: '/search' },
  {
    id: 'ai',
    label: 'IA Asistente',
    icon: Sparkles,
    href: '/ai',
    badge: 'PRO',
    badgeVariant: 'accent',
  },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onSelectNav?: (id: string) => void;
}

export function Sidebar({ isCollapsed, onToggleCollapse, onSelectNav }: SidebarProps) {
  return (
    <aside
      className={cn(
        'relative z-30 flex h-full select-none flex-col border-r border-border bg-card transition-all duration-300 ease-in-out',
        isCollapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Desktop Collapse Toggle — sits on the border itself so it never shares width
          with the logo (that's what was clipping the "MI" badge when collapsed). */}
      <Button
        variant="outline"
        size="icon"
        onClick={onToggleCollapse}
        className="absolute -right-3 top-5 z-40 hidden h-6 w-6 rounded-full border-border bg-card text-muted-foreground shadow-sm hover:text-foreground md:flex"
        aria-label={isCollapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
      >
        {isCollapsed ? (
          <ChevronRight className="h-3.5 w-3.5" />
        ) : (
          <ChevronLeft className="h-3.5 w-3.5" />
        )}
      </Button>

      {/* Brand Header */}
      <div className="flex h-16 items-center border-b border-border px-3.5">
        <NavLink to="/dashboard" className="group flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-sm font-extrabold text-white shadow-md shadow-blue-500/25 ring-4 ring-blue-500/10 transition-transform duration-200 group-hover:scale-105">
            MI
          </div>
          {!isCollapsed && (
            <div className="flex flex-col overflow-hidden leading-tight">
              <span className="truncate text-sm font-bold tracking-tight text-foreground">
                Market Insight
              </span>
              <span className="truncate text-[10px] font-medium text-muted-foreground">
                ChileCompra Analytics
              </span>
            </div>
          )}
        </NavLink>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1.5 overflow-y-auto p-2.5">
        <TooltipProvider delayDuration={150}>
          {NAVIGATION_ITEMS.map((item) => {
            const Icon = item.icon;

            const linkElement = (
              <NavLink
                to={item.href}
                onClick={() => {
                  if (onSelectNav) onSelectNav(item.id);
                }}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center overflow-hidden rounded-xl px-2.5 py-2 text-xs font-medium transition-all duration-150',
                    isActive
                      ? 'bg-gradient-to-r from-blue-50 to-indigo-50/60 font-semibold text-primary shadow-sm ring-1 ring-blue-500/15 dark:from-blue-950/40 dark:to-indigo-950/20 dark:ring-blue-400/10'
                      : 'text-muted-foreground hover:translate-x-0.5 hover:bg-muted/70 hover:text-foreground',
                    isCollapsed ? 'justify-center px-2' : 'justify-between',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute inset-y-1.5 left-0 w-1 rounded-full bg-gradient-to-b from-blue-600 to-indigo-600" />
                    )}

                    <div className="flex min-w-0 items-center gap-2.5">
                      <div
                        className={cn(
                          'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-colors',
                          isActive
                            ? 'bg-white text-blue-600 shadow-sm dark:bg-slate-900/60 dark:text-blue-400'
                            : 'group-hover:shadow-2xs text-muted-foreground group-hover:bg-background group-hover:text-foreground',
                        )}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                      </div>
                      {!isCollapsed && <span className="truncate">{item.label}</span>}
                    </div>

                    {!isCollapsed && item.badge && (
                      <span
                        className={cn(
                          'ml-2 shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none',
                          item.badgeVariant === 'accent'
                            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm shadow-blue-500/30'
                            : 'bg-muted text-muted-foreground',
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );

            if (isCollapsed) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>{linkElement}</TooltipTrigger>
                  <TooltipContent side="right" className="flex items-center gap-1.5">
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="py-0.2 rounded bg-primary/20 px-1 text-[9px] text-primary">
                        {item.badge}
                      </span>
                    )}
                  </TooltipContent>
                </Tooltip>
              );
            }

            return <div key={item.id}>{linkElement}</div>;
          })}
        </TooltipProvider>
      </nav>

      {/* Footer Info */}
      <div className="border-t border-border p-2.5">
        <NavLink
          to="/help"
          className={cn(
            'group flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs text-muted-foreground transition-all duration-150 hover:translate-x-0.5 hover:bg-muted/70 hover:text-foreground',
            isCollapsed && 'justify-center px-2',
          )}
        >
          <div className="group-hover:shadow-2xs flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors group-hover:bg-background group-hover:text-foreground">
            <HelpCircle className="h-4 w-4 shrink-0" />
          </div>
          {!isCollapsed && <span className="truncate">Ayuda y Documentación</span>}
        </NavLink>
      </div>
    </aside>
  );
}
