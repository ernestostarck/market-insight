import { z } from 'zod';

export const organismoSchema = z.object({
  id: z.number().int(),
  codigo: z.string().min(1),
  nombre: z.string().nullable().optional(),
  rut: z.string().nullable().optional(),
  region: z.string().nullable().optional(),
  sector: z.string().nullable().optional(),
  total_licitaciones: z.number().optional(),
  licitaciones_activas: z.number().optional(),
  monto_total_comprado: z.number().optional(),
  dias_pago_promedio: z.number().optional(),
  categoria_principal: z.string().nullable().optional(),
});

export const organismoDetailSchema = organismoSchema.extend({
  total_proveedores_contratados: z.number().optional(),
  evolucion_compras: z
    .array(
      z.object({
        mes: z.string(),
        monto: z.number(),
        licitaciones: z.number(),
      })
    )
    .optional(),
  ranking_proveedores: z
    .array(
      z.object({
        proveedor_nombre: z.string(),
        proveedor_rut: z.string(),
        total_monto: z.number(),
        porcentaje: z.number(),
        contratos: z.number(),
      })
    )
    .optional(),
  ranking_categorias: z
    .array(
      z.object({
        categoria: z.string(),
        total_monto: z.number(),
        porcentaje: z.number(),
      })
    )
    .optional(),
  licitaciones_recientes: z
    .array(
      z.object({
        id: z.number(),
        codigo: z.string(),
        nombre: z.string(),
        monto_estimado: z.number().nullable().optional(),
        estado: z.string().nullable().optional(),
        fecha: z.string().optional(),
      })
    )
    .optional(),
});

export const organismoFiltersSchema = z.object({
  q: z.string().optional(),
  region: z.string().optional(),
  sector: z.string().optional(),
  monto_min: z.number().optional(),
  limit: z.number().optional(),
  cursor: z.string().nullable().optional(),
});
