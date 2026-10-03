/**
 * Global Common TypeScript Types
 */

export interface PaginationParams {
  page: number;
  pageSize: number;
}

export interface CursorPaginationParams {
  limit?: number;
  cursor?: string | null;
}

export interface CursorPage<T> {
  data: T[];
  total: number;
  page_size: number;
  next_cursor: string | null;
  previous_cursor: string | null;
  has_next: boolean;
  has_previous: boolean;
}

/** Server-sorted, offset-paginated page (`/proveedores/ranking`, `/organismos/ranking`). */
export interface OffsetPage<T> {
  data: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface FacetCount {
  value: string;
  count: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page_size?: number;
  page?: number;
  pageSize?: number;
  totalPages?: number;
}

export interface SortingParams {
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
}

export interface DateRangeFilter {
  startDate?: string;
  endDate?: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface ApiError {
  message: string;
  code?: string;
  detail?: string | Record<string, unknown> | Array<unknown>;
  status?: number;
}

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
