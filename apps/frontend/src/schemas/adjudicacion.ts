import { z } from 'zod';

export const adjudicacionSchema = z.object({
  id: z.number().int(),
  licitacion_id: z.number().int(),
  licitacion_codigo: z.string(),
  licitacion_nombre: z.string(),
  proveedor_id: z.number().int(),
  proveedor_rut: z.string(),
  proveedor_razon_social: z.string(),
  organismo_id: z.number().int(),
  organismo_nombre: z.string(),
  monto_adjudicado: z.number(),
  fecha_adjudicacion: z.string(),
  precio_unitario_promedio: z.number().nullable().optional(),
  desviacion_precio_referencial: z.number().nullable().optional(),
});

export const adjudicacionFiltersSchema = z.object({
  q: z.string().optional(),
  proveedor_id: z.number().optional(),
  organismo_id: z.number().optional(),
  categoria: z.string().optional(),
  fecha_desde: z.string().optional(),
  fecha_hasta: z.string().optional(),
  monto_min: z.number().optional(),
  monto_max: z.number().optional(),
});
