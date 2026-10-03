import { z } from 'zod';

export const proveedorSchema = z.object({
  id: z.number().int(),
  rut: z.string().min(1),
  razon_social: z.string().nullable().optional(),
  nombre_fantasia: z.string().nullable().optional(),
  region: z.string().nullable().optional(),
  categoria_principal: z.string().nullable().optional(),
  fecha_registro: z.string().nullable().optional(),
  total_licitaciones_participadas: z.number().optional(),
  total_adjudicaciones: z.number().optional(),
  tasa_exito: z.number().optional(),
  monto_total_adjudicado: z.number().optional(),
});

export const proveedorDetailSchema = proveedorSchema.extend({
  cuota_mercado_estimada: z.number().optional(),
  evolucion_mensual: z
    .array(
      z.object({
        mes: z.string(),
        monto: z.number(),
        adjudicaciones: z.number(),
      }),
    )
    .optional(),
  principales_compradores: z
    .array(
      z.object({
        organismo_nombre: z.string(),
        total_monto: z.number(),
        total_licitaciones: z.number().optional(),
      }),
    )
    .optional(),
  principales_categorias: z
    .array(
      z.object({
        categoria: z.string(),
        total_monto: z.number(),
        porcentaje: z.number(),
      }),
    )
    .optional(),
  ultimas_adjudicaciones: z
    .array(
      z.object({
        id: z.number(),
        codigo_licitacion: z.string(),
        nombre_licitacion: z.string(),
        organismo: z.string().optional(),
        monto: z.number(),
        fecha: z.string(),
      }),
    )
    .optional(),
});

export const proveedorFiltersSchema = z.object({
  q: z.string().optional(),
  region: z.string().optional(),
  rubro: z.string().optional(),
  tasa_minima: z.number().optional(),
  monto_min: z.number().optional(),
  limit: z.number().optional(),
  cursor: z.string().nullable().optional(),
});
