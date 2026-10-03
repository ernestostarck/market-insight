export interface Comprador {
  id: number;
  codigo_usuario?: string | null;
  nombre?: string | null;
  cargo?: string | null;
  rut_unidad?: string | null;
  organismo_id: number;
}
