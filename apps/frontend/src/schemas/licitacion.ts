import { z } from 'zod';

export const licitacionSchema = z.object({
  id: z.number().int(),
  codigo: z.string().min(1),
  nombre: z.string().min(1),
  descripcion: z.string().nullable().optional(),
  estado: z.string().nullable().optional(),
  fecha_publicacion: z.string().nullable().optional(),
  fecha_cierre: z.string().nullable().optional(),
  monto_estimado: z.number().nullable().optional(),
  organismo_id: z.number().int(),
  organismo: z
    .object({
      id: z.number().int(),
      codigo: z.string(),
      nombre: z.string().nullable().optional(),
      rut: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
  categoria: z.string().optional(),
  region: z.string().optional(),
});

export const licitacionItemSchema = z.object({
  id: z.number().int(),
  correlativo: z.number().optional(),
  codigo_producto: z.string().optional(),
  nombre_producto: z.string().optional(),
  rubro: z.string().optional(),
  categoria_unspsc: z.string().optional(),
  cantidad: z.number().optional(),
  unidad_medida: z.string().optional(),
  especificacion_comprador: z.string().optional(),
  precio_unitario_estimado: z.number().optional(),
});

export const licitacionOfertaSchema = z.object({
  id: z.number().int(),
  proveedor_rut: z.string(),
  proveedor_nombre: z.string(),
  monto_total: z.number(),
  fecha_oferta: z.string().optional(),
  estado: z.string().optional(),
  es_adjudicada: z.boolean().optional(),
});

export const licitacionDocumentoSchema = z.object({
  id: z.union([z.number(), z.string()]),
  nombre: z.string(),
  tipo: z.string(),
  fecha: z.string().optional(),
  tamano_kb: z.number().optional(),
  url: z.string().optional(),
});

export const licitacionAdjudicacionSchema = z.object({
  numero_resolucion: z.string().optional(),
  fecha_adjudicacion: z.string().optional(),
  monto_total_adjudicado: z.number().optional(),
  proveedor_ganador_rut: z.string().optional(),
  proveedor_ganador_nombre: z.string().optional(),
  criterios_evaluacion: z
    .array(
      z.object({
        criterio: z.string(),
        ponderacion: z.number(),
        puntaje: z.number(),
      }),
    )
    .optional(),
});

export const licitacionClasificacionIASchema = z.object({
  categoria_predicha: z.string().optional(),
  confianza: z.number().optional(),
  es_relevante_geriatria: z.boolean().optional(),
  es_relevante_discapacidad: z.boolean().optional(),
  conceptos_clave: z.array(z.string()).optional(),
  entidades_extraidas: z
    .array(
      z.object({
        texto: z.string(),
        etiqueta: z.string(),
        confianza: z.number().optional(),
      }),
    )
    .optional(),
  resumen_ejecutivo: z.string().optional(),
  oportunidad_score: z.number().optional(),
  recomendaciones: z.array(z.string()).optional(),
});

export const licitacionDetailSchema = licitacionSchema.extend({
  modalidad: z.string().optional(),
  tipo_convocatoria: z.string().optional(),
  unidad_compra: z.string().optional(),
  organismo_rut: z.string().optional(),
  contacto_nombre: z.string().optional(),
  contacto_email: z.string().optional(),
  link_mercadopublico: z.string().optional(),
  items: z.array(licitacionItemSchema).optional(),
  ofertas: z.array(licitacionOfertaSchema).optional(),
  adjudicacion: licitacionAdjudicacionSchema.nullable().optional(),
  documentos: z.array(licitacionDocumentoSchema).optional(),
  clasificacion_ia: licitacionClasificacionIASchema.nullable().optional(),
});

export const licitacionFiltersSchema = z.object({
  q: z.string().optional(),
  estado: z.string().optional(),
  organismo_id: z.number().int().optional(),
  rubro: z.string().optional(),
  categoria: z.string().optional(),
  region: z.string().optional(),
  monto_min: z.number().optional(),
  monto_max: z.number().optional(),
  fecha_desde: z.string().optional(),
  fecha_hasta: z.string().optional(),
  solo_relevantes: z.boolean().optional(),
  limit: z.number().optional(),
  cursor: z.string().nullable().optional(),
});
