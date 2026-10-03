import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { preferredPageSize } from '@/features/auth/preferences';
import type { Licitacion, LicitacionFilters, CursorPage } from '@/types';

export interface UseLicitacionesOptions {
  initialFilters?: LicitacionFilters;
  defaultLimit?: number;
}

export const FALLBACK_LICITACIONES: Licitacion[] = [
  {
    id: 101,
    codigo: '1057416-24-LE26',
    nombre: 'Adquisición de Camas Clínicas Eléctricas de 4 Secciones para Unidad de Geriatría',
    descripcion:
      'Compra y habilitación de 40 camas clínicas de alta gama con barandas abatibles, trendelenburg y freno centralizado.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-10T09:30:00Z',
    fecha_cierre: '2026-04-10T15:00:00Z',
    monto_estimado: 128500000,
    categoria: 'Equipos Médicos y Camas Clínicas',
    region: 'Metropolitana de Santiago',
    organismo_id: 1,
    organismo: {
      id: 1,
      codigo: 'HSJD-01',
      nombre: 'Hospital San Juan de Dios',
      rut: '61.608.100-2',
    },
  },
  {
    id: 102,
    codigo: '1244-18-LP26',
    nombre:
      'Suministro Continuo de Sillas de Ruedas Neurológicas y Convencionales Pediátricas y Adulto',
    descripcion:
      'Contrato de suministro de 150 sillas de ruedas con soporte cefálico, apoya pies elevables y chasis ultraliviano.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-12T11:00:00Z',
    fecha_cierre: '2026-04-15T16:00:00Z',
    monto_estimado: 89400000,
    categoria: 'Movilidad y Sillas de Ruedas',
    region: 'Metropolitana de Santiago',
    organismo_id: 2,
    organismo: {
      id: 2,
      codigo: 'HSR-02',
      nombre: 'Hospital Dr. Sótero del Río',
      rut: '61.608.200-9',
    },
  },
  {
    id: 103,
    codigo: '721-33-LE26',
    nombre:
      'Grúas Eléctricas de Transferencia y Arnés Bariátrico para Pacientes con Movilidad Reducida',
    descripcion:
      'Adquisición de grúas hospitalarias para movilización segura de pacientes dependientes con arneses lavables de alta resistencia.',
    estado: 'adjudicada',
    fecha_publicacion: '2026-02-15T10:00:00Z',
    fecha_cierre: '2026-03-01T17:00:00Z',
    monto_estimado: 45000000,
    categoria: 'Grúas y Transferencia',
    region: 'Metropolitana de Santiago',
    organismo_id: 3,
    organismo: {
      id: 3,
      codigo: 'SSMC-03',
      nombre: 'Servicio de Salud Metropolitano Central',
      rut: '61.606.300-4',
    },
  },
  {
    id: 104,
    codigo: '1842-12-LR26',
    nombre: 'Convenio de Colchones Antiescaras Viscoelásticos con Sistema de Compresor Alternante',
    descripcion:
      'Provisión masiva de colchones neumáticos para prevención de úlceras por presión en pacientes encamados de larga estadía.',
    estado: 'adjudicada',
    fecha_publicacion: '2026-01-20T08:30:00Z',
    fecha_cierre: '2026-02-28T14:00:00Z',
    monto_estimado: 215000000,
    categoria: 'Colchones Antiescaras e Insumos',
    region: 'Metropolitana de Santiago',
    organismo_id: 4,
    organismo: {
      id: 4,
      codigo: 'CENABAST-04',
      nombre: 'Central de Abastecimiento del SNSS (CENABAST)',
      rut: '61.601.000-K',
    },
  },
  {
    id: 105,
    codigo: '2201-4-LP26',
    nombre:
      'Adquisición e Instalación de Rampas Telescópicas y Plataformas Salvaescaleras Accesibles',
    descripcion:
      'Adecuación de infraestructura para accesibilidad universal de pacientes en sillas de ruedas y adultos mayores.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-08T12:00:00Z',
    fecha_cierre: '2026-04-20T18:00:00Z',
    monto_estimado: 64200000,
    categoria: 'Accesibilidad Universal y Rampas',
    region: 'Biobío',
    organismo_id: 5,
    organismo: {
      id: 5,
      codigo: 'HLH-05',
      nombre: 'Hospital Las Higueras de Talcahuano',
      rut: '61.608.500-8',
    },
  },
  {
    id: 106,
    codigo: '3112-9-LE26',
    nombre: 'Andadores Bariátricos con Ruedas Todo Terreno y Apoyo de Antebrazo Regulable',
    descripcion:
      'Licitación para la adquisición de 80 andadores geriátricos reforzados para el programa de kinesiología motora.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-05T09:00:00Z',
    fecha_cierre: '2026-04-05T12:00:00Z',
    monto_estimado: 28900000,
    categoria: 'Movilidad y Sillas de Ruedas',
    region: 'Metropolitana de Santiago',
    organismo_id: 6,
    organismo: {
      id: 6,
      codigo: 'ING-06',
      nombre: 'Instituto Nacional de Geriatría',
      rut: '61.608.600-4',
    },
  },
  {
    id: 107,
    codigo: '4109-15-LP26',
    nombre: 'Equipamiento de Ayudas Técnicas para Rehabilitación Motora y Estimulación Sensorial',
    descripcion:
      'Kits integrales de rehabilitación para personas con discapacidad severa y secuelas de accidentes cerebrovasculares.',
    estado: 'cerrada',
    fecha_publicacion: '2026-02-01T10:30:00Z',
    fecha_cierre: '2026-03-15T15:30:00Z',
    monto_estimado: 52000000,
    categoria: 'Rehabilitación y Ayudas Técnicas',
    region: 'Magallanes y de la Antártica Chilena',
    organismo_id: 7,
    organismo: {
      id: 7,
      codigo: 'HCM-07',
      nombre: 'Hospital Clínico de Magallanes',
      rut: '61.608.700-0',
    },
  },
  {
    id: 108,
    codigo: '5021-3-LE26',
    nombre: 'Sillas de Evacuación Rápida y Sillas de Baño Inoxidables para Pacientes Dependientes',
    descripcion:
      'Renovación de equipamiento de seguridad y asistencia en higiene para salas de hospitalización de larga estadía.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-14T14:15:00Z',
    fecha_cierre: '2026-04-18T17:00:00Z',
    monto_estimado: 38100000,
    categoria: 'Higiene y Evacuación Asistida',
    region: 'Los Lagos',
    organismo_id: 8,
    organismo: {
      id: 8,
      codigo: 'HPM-08',
      nombre: 'Hospital de Puerto Montt',
      rut: '61.608.800-7',
    },
  },
  {
    id: 109,
    codigo: '6114-22-LR26',
    nombre: 'Camillas de Traslado Radiotransparentes con Barandas Abatibles y Soporte de Suero',
    descripcion:
      '25 camillas para el servicio de urgencia y traslado intra-hospitalario de pacientes de tercera edad.',
    estado: 'adjudicada',
    fecha_publicacion: '2026-01-10T11:00:00Z',
    fecha_cierre: '2026-02-20T16:00:00Z',
    monto_estimado: 76000000,
    categoria: 'Equipos Médicos y Camas Clínicas',
    region: 'Antofagasta',
    organismo_id: 9,
    organismo: {
      id: 9,
      codigo: 'HRA-09',
      nombre: 'Hospital Regional de Antofagasta',
      rut: '61.608.900-3',
    },
  },
  {
    id: 110,
    codigo: '7098-7-LE26',
    nombre:
      'Monitores de Signos Vitales y Oximetría Continua para Sala Geriátrica de Cuidados Medios',
    descripcion:
      'Equipos multiparámetro con conectividad centralizada para monitorización no invasiva de pacientes geriátricos.',
    estado: 'desierta',
    fecha_publicacion: '2026-01-05T08:00:00Z',
    fecha_cierre: '2026-02-10T18:00:00Z',
    monto_estimado: 41500000,
    categoria: 'Monitoreo y Diagnóstico',
    region: 'Coquimbo',
    organismo_id: 10,
    organismo: {
      id: 10,
      codigo: 'HC-10',
      nombre: 'Hospital San Pablo de Coquimbo',
      rut: '61.608.010-6',
    },
  },
  {
    id: 111,
    codigo: '8210-11-LP26',
    nombre:
      'Cojines de Flotación Seca con Celdas de Aire Interconectadas para Prevención de Escaras',
    descripcion:
      'Suministro de cojines ergonómicos de alta densidad para usuarios permanentes de sillas de ruedas.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-01T10:00:00Z',
    fecha_cierre: '2026-04-02T16:00:00Z',
    monto_estimado: 19800000,
    categoria: 'Colchones Antiescaras e Insumos',
    region: 'Metropolitana de Santiago',
    organismo_id: 11,
    organismo: {
      id: 11,
      codigo: 'HSJ-11',
      nombre: 'Hospital San José',
      rut: '61.608.110-K',
    },
  },
  {
    id: 112,
    codigo: '9330-19-LE26',
    nombre:
      'Mesas Puente Hospitalarias Regulables y Sillones de Reposo Reclinables con Elevador Eléctrico',
    descripcion:
      'Mobiliario ergonómico asistido para habitaciones de adultos mayores y unidades de recuperación física.',
    estado: 'publicada',
    fecha_publicacion: '2026-03-15T09:00:00Z',
    fecha_cierre: '2026-04-19T17:30:00Z',
    monto_estimado: 34500000,
    categoria: 'Mobiliario Clínico Geriátrico',
    region: 'Metropolitana de Santiago',
    organismo_id: 12,
    organismo: {
      id: 12,
      codigo: 'HSBA-12',
      nombre: 'Hospital Clínico San Borja Arriarán',
      rut: '61.608.120-7',
    },
  },
];

export function useLicitaciones(options?: UseLicitacionesOptions) {
  const [filters, setFiltersState] = useState<LicitacionFilters>(options?.initialFilters || {});
  const [limit, setLimit] = useState<number>(options?.defaultLimit || preferredPageSize());
  const [activeCursor, setActiveCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<(string | null)[]>([null]);
  const [pageIndex, setPageIndex] = useState<number>(0);

  const queryParams = useMemo(() => {
    const params: Record<string, string | number> = { limit };
    if (activeCursor) params.cursor = activeCursor;
    if (filters.q) params.q = filters.q;
    if (filters.estado && filters.estado !== 'all') params.estado = filters.estado;
    if (filters.organismo_id) params.organismo_id = filters.organismo_id;
    if (filters.monto_min !== undefined) params.monto_min = filters.monto_min;
    if (filters.monto_max !== undefined) params.monto_max = filters.monto_max;
    if (filters.solo_relevantes) params.solo_relevantes = 1;
    return params;
  }, [filters, limit, activeCursor]);

  const query = useQuery<CursorPage<Licitacion>>({
    queryKey: ['licitaciones', queryParams],
    queryFn: async () => {
      return api.get<CursorPage<Licitacion>>('/licitaciones', { params: queryParams });
    },
    staleTime: 2 * 60 * 1000,
  });

  const setFilters = useCallback((newFilters: Partial<LicitacionFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
    setActiveCursor(null);
    setCursorHistory([null]);
    setPageIndex(0);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState({});
    setActiveCursor(null);
    setCursorHistory([null]);
    setPageIndex(0);
  }, []);

  const goToNextPage = useCallback(() => {
    if (query.data?.has_next && query.data.next_cursor) {
      const next = query.data.next_cursor;
      setActiveCursor(next);
      setCursorHistory((prev) => [...prev, next]);
      setPageIndex((prev) => prev + 1);
    }
  }, [query.data]);

  const goToPreviousPage = useCallback(() => {
    if (pageIndex > 0) {
      const newHistory = cursorHistory.slice(0, -1);
      const prevCursor = newHistory[newHistory.length - 1] ?? null;
      setCursorHistory(newHistory);
      setActiveCursor(prevCursor);
      setPageIndex((prev) => Math.max(0, prev - 1));
    }
  }, [cursorHistory, pageIndex]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    filters,
    setFilters,
    resetFilters,
    limit,
    setLimit,
    pageNumber: pageIndex + 1,
    goToNextPage,
    goToPreviousPage,
    hasNextPage: Boolean(query.data?.has_next),
    hasPreviousPage: pageIndex > 0 || Boolean(query.data?.has_previous),
  };
}
