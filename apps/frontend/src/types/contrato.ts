export interface Contrato {
  id: number;
  codigo_contrato?: string | null;
  nombre?: string | null;
  monto_total?: number | null;
  fecha_inicio?: string | null;
  fecha_termino?: string | null;
  licitacion_id?: number | null;
  proveedor_id?: number | null;
  organismo_id?: number | null;
}
