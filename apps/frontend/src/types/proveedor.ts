export interface Proveedor {
  id: number;
  rut: string;
  razon_social?: string | null;
  nombre_fantasia?: string | null;
  region?: string | null;
  categoria_principal?: string | null;
  fecha_registro?: string | null;
  total_licitaciones_participadas?: number;
  total_adjudicaciones?: number;
  tasa_exito?: number;
  monto_total_adjudicado?: number;
}

export interface ProveedorEvolucionItem {
  mes: string;
  monto: number;
  adjudicaciones: number;
}

export interface ProveedorCompradorItem {
  organismo_nombre: string;
  total_monto: number;
  total_licitaciones?: number;
}

export interface ProveedorCategoriaItem {
  categoria: string;
  total_monto: number;
  porcentaje: number;
}

export interface ProveedorAdjudicacionItem {
  id: number;
  codigo_licitacion: string;
  nombre_licitacion: string;
  organismo?: string;
  monto: number;
  fecha: string;
}

export interface ProveedorDetail extends Proveedor {
  cuota_mercado_estimada?: number;
  evolucion_mensual?: ProveedorEvolucionItem[];
  principales_compradores?: ProveedorCompradorItem[];
  principales_categorias?: ProveedorCategoriaItem[];
  ultimas_adjudicaciones?: ProveedorAdjudicacionItem[];
}

export interface ProveedorFilters {
  q?: string;
  region?: string;
  rubro?: string;
  tasa_minima?: number;
  monto_min?: number;
  limit?: number;
  cursor?: string | null;
}
