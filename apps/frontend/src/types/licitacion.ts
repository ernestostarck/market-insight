import type { Organismo } from './organismo';

export type LicitacionEstado =
  'publicada' | 'cerrada' | 'desierta' | 'adjudicada' | 'revocada' | 'suspendida' | string;

export interface LicitacionItem {
  id: number;
  correlativo?: number;
  codigo_producto?: string;
  nombre_producto?: string;
  rubro?: string;
  categoria_unspsc?: string;
  cantidad?: number;
  unidad_medida?: string;
  especificacion_comprador?: string;
  precio_unitario_estimado?: number;
}

export interface LicitacionOferta {
  id: number;
  proveedor_rut: string;
  proveedor_nombre: string;
  monto_total: number;
  fecha_oferta?: string;
  estado?: string;
  es_adjudicada?: boolean;
}

export interface LicitacionDocumento {
  id: number | string;
  nombre: string;
  tipo: 'bases' | 'anexo' | 'aclaracion' | 'resolucion' | 'acta' | string;
  fecha?: string;
  tamano_kb?: number;
  url?: string;
}

export interface LicitacionAdjudicacion {
  numero_resolucion?: string;
  fecha_adjudicacion?: string;
  monto_total_adjudicado?: number;
  proveedor_ganador_rut?: string;
  proveedor_ganador_nombre?: string;
  criterios_evaluacion?: Array<{
    criterio: string;
    ponderacion: number;
    puntaje: number;
  }>;
}

export interface LicitacionClasificacionIA {
  categoria_predicha?: string;
  confianza?: number;
  es_relevante_geriatria?: boolean;
  es_relevante_discapacidad?: boolean;
  conceptos_clave?: string[];
  entidades_extraidas?: Array<{
    texto: string;
    etiqueta: string;
    confianza?: number;
  }>;
  resumen_ejecutivo?: string;
  oportunidad_score?: number;
  recomendaciones?: string[];
}

export interface Licitacion {
  id: number;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  estado?: LicitacionEstado | null;
  fecha_publicacion?: string | null;
  fecha_cierre?: string | null;
  monto_estimado?: number | null;
  organismo_id: number;
  organismo?: Organismo | null;
  categoria?: string;
  region?: string;
}

export interface LicitacionDetail extends Licitacion {
  modalidad?: string;
  tipo_convocatoria?: string;
  unidad_compra?: string;
  region?: string;
  organismo_rut?: string;
  contacto_nombre?: string;
  contacto_email?: string;
  link_mercadopublico?: string;
  items?: LicitacionItem[];
  ofertas?: LicitacionOferta[];
  adjudicacion?: LicitacionAdjudicacion | null;
  documentos?: LicitacionDocumento[];
  clasificacion_ia?: LicitacionClasificacionIA | null;
}

export interface LicitacionFilters {
  q?: string;
  estado?: string;
  organismo_id?: number;
  rubro?: string;
  categoria?: string;
  region?: string;
  monto_min?: number;
  monto_max?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  solo_relevantes?: boolean;
  limit?: number;
  cursor?: string | null;
}
