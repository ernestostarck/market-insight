import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { MetricKpiCard } from '@/components/charts/MetricKpiCard';
import { RecentTendersTable } from '@/features/dashboard/components/RecentTendersTable';
import { RecentAwardsTable } from '@/features/dashboard/components/RecentAwardsTable';
import type { Licitacion } from '@/types/licitacion';
import type { Adjudicacion } from '@/types/adjudicacion';

describe('Dashboard & Chart Components', () => {
  describe('MetricKpiCard', () => {
    it('renders title, formatted value, and positive change', () => {
      render(
        <MetricKpiCard
          title="Monto Total Adjudicado"
          value="$1.845M"
          change={14.8}
          changeLabel="crecimiento mensual"
          helper="Volumen transaccionado en el período activo"
        />,
      );

      expect(screen.getByText('Monto Total Adjudicado')).toBeInTheDocument();
      expect(screen.getByText('$1.845M')).toBeInTheDocument();
      expect(screen.getByText(/14.8%/)).toBeInTheDocument();
      expect(screen.getByText('crecimiento mensual')).toBeInTheDocument();
    });

    it('renders negative change indicator', () => {
      render(
        <MetricKpiCard
          title="Organismos Compradores"
          value={34}
          change={-2.1}
          changeLabel="variación"
        />,
      );

      expect(screen.getByText('Organismos Compradores')).toBeInTheDocument();
      expect(screen.getByText(/2.1%/)).toBeInTheDocument();
    });
  });

  describe('RecentTendersTable', () => {
    const mockTenders: Licitacion[] = [
      {
        id: 1,
        codigo: '1057-22-LR26',
        nombre: 'Suministro de Camas Clínicas Hospitalarias',
        estado: 'publicada',
        monto_estimado: 125000000,
        fecha_publicacion: '2026-06-18',
        organismo_id: 1,
        organismo: { id: 1, codigo: 'H01', nombre: 'Hospital San Borja' },
      },
    ];

    it('renders tender table columns and tender data', () => {
      render(
        <MemoryRouter>
          <RecentTendersTable tenders={mockTenders} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Licitaciones Recientes')).toBeInTheDocument();
      expect(screen.getByText('1057-22-LR26')).toBeInTheDocument();
      expect(screen.getByText('Suministro de Camas Clínicas Hospitalarias')).toBeInTheDocument();
      expect(screen.getByText('Hospital San Borja')).toBeInTheDocument();
      expect(screen.getByText('Publicada')).toBeInTheDocument();
    });
  });

  describe('RecentAwardsTable', () => {
    const mockAwards: Adjudicacion[] = [
      {
        id: 1,
        licitacion_id: 101,
        licitacion_codigo: '2234-15-LE26',
        licitacion_nombre: 'Adquisición de Sillas de Ruedas Bariátricas',
        proveedor_id: 1,
        proveedor_rut: '761234567',
        proveedor_razon_social: 'Ortopedia Técnica Chile SpA',
        organismo_id: 2,
        organismo_nombre: 'SENAMA',
        monto_adjudicado: 74500000,
        fecha_adjudicacion: '2026-06-19',
      },
    ];

    it('renders award table columns, supplier, and formatted RUT', () => {
      render(
        <MemoryRouter>
          <RecentAwardsTable awards={mockAwards} />
        </MemoryRouter>,
      );

      expect(screen.getByText('Últimas Adjudicaciones')).toBeInTheDocument();
      expect(screen.getByText('2234-15-LE26')).toBeInTheDocument();
      expect(screen.getByText('Ortopedia Técnica Chile SpA')).toBeInTheDocument();
      expect(screen.getByText(/76\.123\.456-7/)).toBeInTheDocument();
      expect(screen.getByText('SENAMA')).toBeInTheDocument();
    });
  });
});
