import { z } from 'zod';

export const aiConfidenceLevelSchema = z.enum(['alta', 'media', 'baja']);
export const aiReviewStatusSchema = z.enum(['pendiente', 'aceptada', 'corregida']);

export const aiEntitySchema = z.object({
  tipo: z.string(),
  texto: z.string(),
  confianza: z.number(),
});

export const aiProductDetectedSchema = z.object({
  nombre: z.string(),
  atributos: z.record(z.string()),
  confianza: z.number(),
});

export const aiDocumentProcessedSchema = z.object({
  id: z.number().int(),
  licitacion_id: z.number().int(),
  licitacion_codigo: z.string(),
  licitacion_nombre: z.string(),
  organismo: z.string(),
  monto_estimado: z.number(),
  nombre_archivo: z.string(),
  fecha_procesamiento: z.string(),
  categoria_detectada: z.string(),
  subcategoria_detectada: z.string(),
  confianza: z.number(),
  metodo_clasificacion: z.enum([
    'Zero-Shot LLM',
    'Hybrid Semantic + Keyword',
    'TF-IDF Ensemble',
  ]),
  version_modelo: z.string(),
  version_taxonomia: z.string(),
  modelo_embeddings: z.string(),
  entidades: z.array(aiEntitySchema),
  conceptos: z.array(z.string()),
  productos_detectados: z.array(aiProductDetectedSchema),
  estado_revision: aiReviewStatusSchema,
  revisado_por: z.string().optional(),
  fecha_revision: z.string().optional(),
  comentarios_revision: z.string().optional(),
});

export const aiReviewActionSchema = z.object({
  documentId: z.number().int(),
  action: z.enum(['accept', 'correct']),
  correctedCategoria: z.string().optional(),
  correctedSubcategoria: z.string().optional(),
  reviewer: z.string(),
  notes: z.string().optional(),
});

export const serviceStatusSchema = z.enum(['operativo', 'degradado', 'sincronizando', 'error']);

export const dataQualityStatusSchema = z.object({
  ultima_actualizacion: z.string(),
  frecuencia_actualizacion: z.string(),
  total_licitaciones: z.number(),
  total_documentos: z.number(),
  total_clasificaciones_ia: z.number(),
  estado_etl: serviceStatusSchema,
  estado_api: serviceStatusSchema,
  estado_nlp: serviceStatusSchema,
  latencia_api_ms: z.number(),
  tasa_completitud: z.number(),
  advertencias: z.array(z.string()),
});
