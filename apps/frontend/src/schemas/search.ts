import { z } from 'zod';

export const searchEntitySchema = z.enum(['licitacion', 'proveedor', 'organismo']);

export const searchQuerySchema = z.object({
  query: z.string().min(2, 'La búsqueda debe tener al menos 2 caracteres'),
  entities: z.array(searchEntitySchema).optional(),
  limit_per_entity: z.number().int().min(1).max(50).default(10),
});

export const searchResultSchema = z.object({
  entity_type: searchEntitySchema,
  id: z.number().int(),
  title: z.string(),
  subtitle: z.string().nullable().optional(),
  code: z.string().nullable().optional(),
  metadata: z.record(z.union([z.string(), z.number(), z.boolean(), z.null()])).optional(),
  score: z.number().optional(),
  semantic_score: z.number().optional(),
  keyword_score: z.number().optional(),
});
