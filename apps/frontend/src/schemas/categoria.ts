import { z } from 'zod';

export const categoriaNivelSchema = z.enum(['segmento', 'familia', 'clase', 'producto']);

export const categoriaSchema = z.object({
  codigo: z.string(),
  nombre: z.string(),
  nivel: categoriaNivelSchema,
  codigo_padre: z.string().nullable().optional(),
  descripcion: z.string().optional(),
  total_licitaciones: z.number(),
  monto_total: z.number(),
  tasa_crecimiento: z.number(),
  total_proveedores: z.number(),
  total_organismos: z.number(),
});

export const categoriaProveedorItemSchema = z.object({
  proveedor_nombre: z.string(),
  proveedor_rut: z.string(),
  monto_adjudicado: z.number(),
  cuota: z.number(),
});

export const categoriaOrganismoItemSchema = z.object({
  organismo_nombre: z.string(),
  monto_comprado: z.number(),
  total_licitaciones: z.number(),
});

export const categoriaDetailSchema = categoriaSchema.extend({
  principales_proveedores: z.array(categoriaProveedorItemSchema).optional(),
  principales_organismos: z.array(categoriaOrganismoItemSchema).optional(),
  subcategorias: z.array(categoriaSchema).optional(),
});

export const categoriaFiltersSchema = z.object({
  q: z.string().optional(),
  nivel: z.union([categoriaNivelSchema, z.literal('all')]).optional(),
  monto_min: z.number().optional(),
});
