import { z } from 'zod';

export const paginationParamsSchema = z.object({
  page: z.number().int().min(1).default(1),
  pageSize: z.number().int().min(1).max(100).default(20),
});

export const cursorPaginationParamsSchema = z.object({
  limit: z.number().int().min(1).max(100).default(50),
  cursor: z.string().nullable().optional(),
});

export const sortingParamsSchema = z.object({
  sortBy: z.string().optional(),
  sortDirection: z.enum(['asc', 'desc']).default('desc'),
});

export const dateRangeSchema = z.object({
  startDate: z.string().optional(),
  endDate: z.string().optional(),
});

export function createCursorPageSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    total: z.number().int().min(0),
    page_size: z.number().int().min(1),
    next_cursor: z.string().nullable(),
    previous_cursor: z.string().nullable(),
    has_next: z.boolean(),
    has_previous: z.boolean(),
  });
}

export function createPaginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number().int().min(0),
    page: z.number().int().min(1),
    pageSize: z.number().int().min(1),
    totalPages: z.number().int().min(0),
  });
}

/**
 * Validate API responses with safe fallback and console warning in dev
 */
export function validateSchema<T>(schema: z.ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('API contract schema validation failed:', result.error.format());
    }
    return data as T;
  }
  return result.data;
}
