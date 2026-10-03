import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  active?: boolean;
}

interface BreadcrumbsProps {
  items?: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumbs({ items = [], className }: BreadcrumbsProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center text-xs text-muted-foreground', className)}
    >
      <ol className="flex items-center space-x-1.5">
        <li className="inline-flex items-center">
          <a
            href="#/dashboard"
            className="flex items-center gap-1 transition-colors hover:text-foreground"
          >
            <Home className="h-3.5 w-3.5" />
            <span>Inicio</span>
          </a>
        </li>

        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.label} className="inline-flex items-center space-x-1.5">
              <ChevronRight className="h-3 w-3 text-muted-foreground/60" />
              {isLast || item.active ? (
                <span className="font-medium text-foreground">{item.label}</span>
              ) : (
                <a href={item.href || '#'} className="transition-colors hover:text-foreground">
                  {item.label}
                </a>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
