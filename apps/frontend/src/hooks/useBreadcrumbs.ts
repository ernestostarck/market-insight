import { useLocation } from 'react-router-dom';
import type { BreadcrumbItem } from '@/components/layout/Breadcrumbs';

const ROUTE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  mercado: 'Mercado',
  licitaciones: 'Licitaciones',
  proveedores: 'Proveedores',
  organismos: 'Organismos',
  categorias: 'Categorías',
  rubros: 'Rubros',
  perfil: 'Mi perfil',
  configuracion: 'Configuración',
  adjudicaciones: 'Adjudicaciones',
  'ordenes-compra': 'Órdenes de Compra',
  analytics: 'Analytics',
  search: 'Búsqueda',
  ai: 'IA Asistente',
};

export function useBreadcrumbs(): BreadcrumbItem[] {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  if (segments.length === 0) {
    return [{ label: 'Dashboard', active: true }];
  }

  const breadcrumbs: BreadcrumbItem[] = [];
  let currentPath = '';

  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    const isLast = index === segments.length - 1;

    let label = ROUTE_LABELS[segment] || decodeURIComponent(segment);
    if (index > 0 && !ROUTE_LABELS[segment]) {
      label = `Detalle: ${segment}`;
    }

    breadcrumbs.push({
      label,
      href: isLast ? undefined : currentPath,
      active: isLast,
    });
  });

  return breadcrumbs;
}
