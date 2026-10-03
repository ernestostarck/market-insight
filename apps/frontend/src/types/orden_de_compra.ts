export interface OrdenDeCompra {
  id: number;
  codigo: string;
  nombre?: string | null;
  estado?: string | null;
  monto_total?: number | null;
  moneda?: string | null;
  fecha_creacion?: string | null;
  fecha_envio?: string | null;
  organismo_id?: number | null;
  organismo_nombre?: string | null;
  proveedor_id?: number | null;
  proveedor_nombre?: string | null;
  proveedor_rut?: string | null;
  licitacion_id?: number | null;
  licitacion_codigo?: string | null;
  items_count?: number;
}

export interface OrdenDeCompraFilters {
  q?: string;
  estado?: string;
  organismo_id?: number;
  proveedor_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  monto_min?: number;
}
