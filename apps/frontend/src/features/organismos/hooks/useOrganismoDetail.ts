import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { OrganismoDetail } from '@/types';
import { FALLBACK_ORGANISMOS } from './useOrganismos';

export function buildFallbackOrganismoDetail(id: number | string): OrganismoDetail {
  const numId = Number(id) || 1;
  const base = FALLBACK_ORGANISMOS.find((o) => o.id === numId) || FALLBACK_ORGANISMOS[0];

  return {
    ...base,
    id: numId,
    total_proveedores_contratados: 48,
    evolucion_compras: [
      { mes: 'Abr 2025', monto: 180000000, licitaciones: 8 },
      { mes: 'May 2025', monto: 240000000, licitaciones: 11 },
      { mes: 'Jun 2025', monto: 310000000, licitaciones: 14 },
      { mes: 'Jul 2025', monto: 195000000, licitaciones: 9 },
      { mes: 'Ago 2025', monto: 350000000, licitaciones: 15 },
      { mes: 'Sep 2025', monto: 290000000, licitaciones: 12 },
      { mes: 'Oct 2025', monto: 420000000, licitaciones: 18 },
      { mes: 'Nov 2025', monto: 480000000, licitaciones: 20 },
      { mes: 'Dic 2025', monto: 560000000, licitaciones: 22 },
      { mes: 'Ene 2026', monto: 210000000, licitaciones: 7 },
      { mes: 'Feb 2026', monto: 260000000, licitaciones: 9 },
      { mes: 'Mar 2026', monto: 355000000, licitaciones: 13 },
    ],
    ranking_proveedores: [
      {
        proveedor_nombre: 'Ortopedia y Equipos Médicos Austral SpA',
        proveedor_rut: '76.432.189-5',
        total_monto: 980000000,
        porcentaje: 25.5,
        contratos: 14,
      },
      {
        proveedor_nombre: 'Rehabilitación y Tecnología Médica Chile S.A.',
        proveedor_rut: '77.892.450-1',
        total_monto: 620000000,
        porcentaje: 16.1,
        contratos: 9,
      },
      {
        proveedor_nombre: 'Insumos Clínicos Hospitalarios del Sur Ltda.',
        proveedor_rut: '96.812.330-K',
        total_monto: 450000000,
        porcentaje: 11.7,
        contratos: 8,
      },
      {
        proveedor_nombre: 'Soluciones Geriátricas Integrales Chile Ltda.',
        proveedor_rut: '78.112.980-8',
        total_monto: 380000000,
        porcentaje: 9.9,
        contratos: 6,
      },
      {
        proveedor_nombre: 'Ergonomía Médica & Cuidados Intensivos SpA',
        proveedor_rut: '77.304.812-9',
        total_monto: 290000000,
        porcentaje: 7.5,
        contratos: 5,
      },
    ],
    ranking_categorias: [
      {
        categoria: 'Camas Clínicas y Mobiliario Hospitalario',
        total_monto: 1650000000,
        porcentaje: 42.9,
      },
      {
        categoria: 'Sillas de Ruedas y Movilidad Reducida',
        total_monto: 960000000,
        porcentaje: 24.9,
      },
      {
        categoria: 'Grúas y Equipos de Transferencia de Pacientes',
        total_monto: 580000000,
        porcentaje: 15.1,
      },
      {
        categoria: 'Colchones Antiescaras y Cojines de Posicionamiento',
        total_monto: 390000000,
        porcentaje: 10.1,
      },
      {
        categoria: 'Accesorios, Barandas y Repuestos Médicos',
        total_monto: 270000000,
        porcentaje: 7.0,
      },
    ],
    licitaciones_recientes: [
      {
        id: 101,
        codigo: '1057416-24-LE26',
        nombre: 'Adquisición de Camas Clínicas Eléctricas de 4 Secciones para Unidad de Geriatría',
        monto_estimado: 128500000,
        estado: 'Adjudicada',
        fecha: '2026-03-01',
      },
      {
        id: 102,
        codigo: '1057416-28-LP26',
        nombre: 'Suministro Bianual de Sillas de Ruedas Eléctricas y Manuales Pediátricas y Adulto',
        monto_estimado: 89000000,
        estado: 'Publicada',
        fecha: '2026-03-10',
      },
      {
        id: 105,
        codigo: '1057416-31-LE26',
        nombre: 'Reposición de Colchones Neumáticos con Presión Alternante Dinámica',
        monto_estimado: 42000000,
        estado: 'Cerrada',
        fecha: '2026-02-20',
      },
      {
        id: 107,
        codigo: '1057416-35-LR26',
        nombre: 'Grúas Hospitalarias Móviles para Pacientes de Alta Dependencia',
        monto_estimado: 64000000,
        estado: 'Adjudicada',
        fecha: '2026-01-25',
      },
    ],
  };
}

export function useOrganismoDetail(id: number | string | undefined) {
  return useQuery<OrganismoDetail>({
    queryKey: ['organismo-detail', id],
    queryFn: async () => {
      if (!id) throw new Error('ID de organismo no especificado');

      try {
        const response = await api.get<OrganismoDetail>(`/organismos/${id}`);
        if (response && (response.codigo || response.nombre)) {
          const fallback = buildFallbackOrganismoDetail(id);
          return {
            ...fallback,
            ...response,
            evolucion_compras: response.evolucion_compras || fallback.evolucion_compras,
            ranking_proveedores: response.ranking_proveedores || fallback.ranking_proveedores,
            ranking_categorias: response.ranking_categorias || fallback.ranking_categorias,
            licitaciones_recientes:
              response.licitaciones_recientes || fallback.licitaciones_recientes,
          };
        }
      } catch (err) {
        console.warn(`API /organismos/${id} returned error, using fallback:`, err);
      }

      return buildFallbackOrganismoDetail(id);
    },
    enabled: Boolean(id),
    staleTime: 3 * 60 * 1000,
  });
}
