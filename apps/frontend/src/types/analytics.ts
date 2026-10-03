export interface MarketMonthlyRead {
  mes: string;
  total_licitaciones: number;
  total_adjudicaciones: number;
  monto_total_adjudicado: number | string;
}

export interface SupplierPerformanceRead {
  razon_social: string;
  rut: string;
  total_adjudicaciones: number;
  monto_total_adjudicado: number | string;
  ratio_adjudicacion_promedio: number | string | null;
  ultima_adjudicacion?: string | null;
}

export interface CategorySpendingRead {
  categoria: string;
  codigo_categoria: string;
  gasto_total_oc: number | string;
  numero_ordenes_compra: number;
  gasto_promedio_oc: number | string;
}

export interface BidderRangeBucket {
  rango_oferentes: string;
  total_procesos: number;
  porcentaje: number;
}

export interface CompetitionSummaryRead {
  oferentes_promedio: number | null;
  margen_descuento_promedio: number | null;
  total_adjudicaciones_con_oferentes: number;
  distribucion_oferentes: BidderRangeBucket[];
}

export interface DashboardKpis {
  licitaciones_activas: number;
  monto_total_adjudicado_mes: number;
  proveedores_activos: number;
  organismos_compradores: number;
  tasa_crecimiento_monto: number;
  match_semantico_promedio: number;
}

