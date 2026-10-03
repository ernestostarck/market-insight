export interface Organismo {
  id: number;
  codigo: string;
  nombre?: string | null;
  rut?: string | null;
  region?: string | null;
  sector?: string | null;
  total_licitaciones?: number;
  licitaciones_activas?: number;
  monto_total_comprado?: number;
  dias_pago_promedio?: number;
  categoria_principal?: string | null;
}

export interface OrganismoEvolucionItem {
  mes: string;
  monto: number;
  licitaciones: number;
}

export interface OrganismoProveedorRankingItem {
  proveedor_nombre: string;
  proveedor_rut: string;
  total_monto: number;
  porcentaje: number;
  contratos: number;
}

export interface OrganismoCategoriaRankingItem {
  categoria: string;
  total_monto: number;
  porcentaje: number;
}

export interface OrganismoLicitacionReciente {
  id: number;
  codigo: string;
  nombre: string;
  monto_estimado?: number | null;
  estado?: string | null;
  fecha?: string;
}

export interface OrganismoDetail extends Organismo {
  total_proveedores_contratados?: number;
  evolucion_compras?: OrganismoEvolucionItem[];
  ranking_proveedores?: OrganismoProveedorRankingItem[];
  ranking_categorias?: OrganismoCategoriaRankingItem[];
  licitaciones_recientes?: OrganismoLicitacionReciente[];
}

export interface OrganismoFilters {
  q?: string;
  region?: string;
  sector?: string;
  monto_min?: number;
  limit?: number;
  cursor?: string | null;
}
