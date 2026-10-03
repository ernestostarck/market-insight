export interface Categoria {
  id: number;
  codigo: string | null;
  nombre: string | null;
  segmento: string | null;
  familia: string | null;
  clase: string | null;
  total_licitaciones: number;
  monto_total: number;
  total_proveedores: number;
  total_organismos: number;
}

export interface CategoriaProveedorItem {
  proveedor_id: number;
  proveedor_nombre: string | null;
  proveedor_rut: string | null;
  monto_adjudicado: number;
  cuota: number;
}

export interface CategoriaOrganismoItem {
  organismo_id: number;
  organismo_nombre: string | null;
  monto_comprado: number;
  total_licitaciones: number;
}

export interface CategoriaDetail extends Categoria {
  principales_proveedores: CategoriaProveedorItem[];
  principales_organismos: CategoriaOrganismoItem[];
}

export interface CategoriaFilters {
  q?: string;
  monto_minimo?: number;
  limit?: number;
  cursor?: string | null;
}
