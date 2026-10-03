import { z } from 'zod';

export const ordenDeCompraSchema = z.object({
  id: z.number().int(),
  codigo: z.string(),
  nombre: z.string().nullable().optional(),
  estado: z.string().nullable().optional(),
  monto_total: z.number().nullable().optional(),
  moneda: z.string().nullable().optional(),
  fecha_creacion: z.string().nullable().optional(),
  fecha_envio: z.string().nullable().optional(),
  organismo_id: z.number().nullable().optional(),
  organismo_nombre: z.string().nullable().optional(),
  proveedor_id: z.number().nullable().optional(),
  proveedor_nombre: z.string().nullable().optional(),
  proveedor_rut: z.string().nullable().optional(),
  licitacion_id: z.number().nullable().optional(),
  licitacion_codigo: z.string().nullable().optional(),
  items_count: z.number().optional(),
});

export const ordenDeCompraFiltersSchema = z.object({
  q: z.string().optional(),
  estado: z.string().optional(),
  organismo_id: z.number().optional(),
  proveedor_id: z.number().optional(),
  fecha_desde: z.string().optional(),
  fecha_hasta: z.string().optional(),
  monto_min: z.number().optional(),
});
