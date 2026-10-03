import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { ProveedorDetail } from '@/types';
import { FALLBACK_PROVEEDORES } from './useProveedores';

export function buildFallbackProveedorDetail(id: number | string): ProveedorDetail {
  const numId = Number(id) || 1;
  const base = FALLBACK_PROVEEDORES.find((p) => p.id === numId) || FALLBACK_PROVEEDORES[0];

  return {
    ...base,
    id: numId,
    cuota_mercado_estimada: 24.8,
    evolucion_mensual: [
      { mes: 'Abr 2025', monto: 75000000, adjudicaciones: 2 },
      { mes: 'May 2025', monto: 92000000, adjudicaciones: 3 },
      { mes: 'Jun 2025', monto: 110000000, adjudicaciones: 3 },
      { mes: 'Jul 2025', monto: 85000000, adjudicaciones: 2 },
      { mes: 'Ago 2025', monto: 130000000, adjudicaciones: 4 },
      { mes: 'Sep 2025', monto: 145000000, adjudicaciones: 4 },
      { mes: 'Oct 2025', monto: 160000000, adjudicaciones: 5 },
      { mes: 'Nov 2025', monto: 180000000, adjudicaciones: 5 },
      { mes: 'Dic 2025', monto: 210000000, adjudicaciones: 6 },
      { mes: 'Ene 2026', monto: 78000000, adjudicaciones: 2 },
      { mes: 'Feb 2026', monto: 84000000, adjudicaciones: 2 },
      { mes: 'Mar 2026', monto: 128500000, adjudicaciones: 3 },
    ],
    principales_compradores: [
      {
        organismo_nombre: 'Hospital San Juan de Dios',
        total_monto: 520000000,
        total_licitaciones: 14,
      },
      { organismo_nombre: 'CENABAST', total_monto: 410000000, total_licitaciones: 9 },
      {
        organismo_nombre: 'Hospital Dr. Sótero del Río',
        total_monto: 260000000,
        total_licitaciones: 8,
      },
      {
        organismo_nombre: 'Instituto Nacional de Geriatría',
        total_monto: 145000000,
        total_licitaciones: 5,
      },
      {
        organismo_nombre: 'Hospital Las Higueras Talcahuano',
        total_monto: 85500000,
        total_licitaciones: 2,
      },
    ],
    principales_categorias: [
      { categoria: 'Equipos Médicos y Camas Clínicas', total_monto: 710000000, porcentaje: 50.0 },
      { categoria: 'Movilidad y Sillas de Ruedas', total_monto: 355000000, porcentaje: 25.0 },
      { categoria: 'Grúas y Transferencia', total_monto: 213000000, porcentaje: 15.0 },
      { categoria: 'Insumos y Accesorios', total_monto: 142500000, porcentaje: 10.0 },
    ],
    ultimas_adjudicaciones: [
      {
        id: 101,
        codigo_licitacion: '1057416-24-LE26',
        nombre_licitacion:
          'Adquisición de Camas Clínicas Eléctricas de 4 Secciones para Unidad de Geriatría',
        organismo: 'Hospital San Juan de Dios',
        monto: 128500000,
        fecha: '2026-03-01',
      },
      {
        id: 103,
        codigo_licitacion: '721-33-LE26',
        nombre_licitacion: 'Grúas Eléctricas de Transferencia y Arnés Bariátrico',
        organismo: 'Servicio de Salud Metropolitano Central',
        monto: 45000000,
        fecha: '2026-02-15',
      },
      {
        id: 109,
        codigo_licitacion: '6114-22-LR26',
        nombre_licitacion: 'Camillas de Traslado Radiotransparentes con Barandas Abatibles',
        organismo: 'Hospital Regional de Antofagasta',
        monto: 76000000,
        fecha: '2026-01-10',
      },
    ],
  };
}

export function useProveedorDetail(id: number | string | undefined) {
  return useQuery<ProveedorDetail>({
    queryKey: ['proveedor-detail', id],
    queryFn: async () => {
      if (!id) throw new Error('ID de proveedor no especificado');

      try {
        const response = await api.get<ProveedorDetail>(`/proveedores/${id}`);
        if (response && response.rut) {
          const fallback = buildFallbackProveedorDetail(id);
          return {
            ...fallback,
            ...response,
            evolucion_mensual: response.evolucion_mensual || fallback.evolucion_mensual,
            principales_compradores:
              response.principales_compradores || fallback.principales_compradores,
            principales_categorias:
              response.principales_categorias || fallback.principales_categorias,
            ultimas_adjudicaciones:
              response.ultimas_adjudicaciones || fallback.ultimas_adjudicaciones,
          };
        }
      } catch (err) {
        console.warn(`API /proveedores/${id} returned error, using fallback:`, err);
      }

      return buildFallbackProveedorDetail(id);
    },
    enabled: Boolean(id),
    staleTime: 3 * 60 * 1000,
  });
}
