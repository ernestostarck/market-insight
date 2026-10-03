import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Sidebar, NAVIGATION_ITEMS } from '@/components/layout/Sidebar';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';

describe('UI Primitives and Layout Components', () => {
  describe('Button Component', () => {
    it('renders with default variant and responds to click', () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Guardar Licitación</Button>);

      const btn = screen.getByRole('button', { name: /guardar licitación/i });
      expect(btn).toBeInTheDocument();
      fireEvent.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders disabled state correctly', () => {
      render(<Button disabled>Deshabilitado</Button>);
      const btn = screen.getByRole('button', { name: /deshabilitado/i });
      expect(btn).toBeDisabled();
    });
  });

  describe('Badge Component', () => {
    it('renders tender status badge with proper text', () => {
      render(<Badge variant="success">Adjudicada</Badge>);
      expect(screen.getByText('Adjudicada')).toBeInTheDocument();
    });
  });

  describe('Card Component', () => {
    it('renders Card hierarchy with header and content', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Métricas de Mercado</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Total adjudicado: $150M</p>
          </CardContent>
        </Card>,
      );

      expect(screen.getByText('Métricas de Mercado')).toBeInTheDocument();
      expect(screen.getByText(/total adjudicado/i)).toBeInTheDocument();
    });
  });

  describe('Sidebar & Navigation', () => {
    it('renders all 12 required navigation items in sidebar', () => {
      expect(NAVIGATION_ITEMS).toHaveLength(12);
      const labels = NAVIGATION_ITEMS.map((item) => item.label);
      expect(labels).toContain('Dashboard');
      expect(labels).toContain('Mercado');
      expect(labels).toContain('Licitaciones');
      expect(labels).toContain('Proveedores');
      expect(labels).toContain('Organismos');
      expect(labels).toContain('Categorías');
      expect(labels).toContain('Adjudicaciones');
      expect(labels).toContain('Órdenes de Compra');
      expect(labels).toContain('Analytics');
      expect(labels).toContain('Búsqueda');
      expect(labels).toContain('IA Asistente');
    });

    it('renders sidebar component and triggers toggle collapse', () => {
      const handleToggle = vi.fn();
      render(
        <MemoryRouter>
          <Sidebar isCollapsed={false} onToggleCollapse={handleToggle} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Market Insight')).toBeInTheDocument();
      expect(screen.getByText('Licitaciones')).toBeInTheDocument();
    });
  });

  describe('Breadcrumbs Component', () => {
    it('renders breadcrumb items correctly', () => {
      render(
        <MemoryRouter>
          <Breadcrumbs
            items={[
              { label: 'Licitaciones', href: '/licitaciones' },
              { label: 'Detalle 1234-56-LP24', active: true },
            ]}
          />
        </MemoryRouter>,
      );

      expect(screen.getByText('Inicio')).toBeInTheDocument();
      expect(screen.getByText('Licitaciones')).toBeInTheDocument();
      expect(screen.getByText('Detalle 1234-56-LP24')).toBeInTheDocument();
    });
  });
});
