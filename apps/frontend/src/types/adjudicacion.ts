export interface Adjudicacion {
  id: number;
  licitacion_id: number;
  licitacion_codigo: string;
  licitacion_nombre: string;
  proveedor_id: number;
  proveedor_rut: string;
  proveedor_razon_social: string;
  organismo_id: number;
  organismo_nombre: string;
  monto_adjudicado: number;
  fecha_adjudicacion: string;
  precio_unitario_promedio?: number | null;
  desviacion_precio_referencial?: number | null;
}

export interface AdjudicacionFilters {
  q?: string;
  proveedor_id?: number;
  organismo_id?: number;
  categoria?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  monto_min?: number;
  monto_max?: number;
}
