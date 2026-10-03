"""create datamarts and supporting views (Fase 4 - Iteración 4)

Revision ID: b642bda69c3d
Revises: 20260807_0006
Create Date: 2026-08-08 13:05:43.943384

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b642bda69c3d'
down_revision = '20260807_0006'
branch_labels = None
depends_on = None

_DW = "dw"
_ANALYTICS = "analytics"
_SUPPLIERS_MART = "suppliers_mart"
_CATEGORIES_MART = "categories_mart"
_DISABILITY_MART = "disability_market_mart"
_DQ_VIEWS = "dq_views"
_LINEAGE_VIEWS = "lineage_views"


def upgrade() -> None:
    # =====================================================================
    # 1. Create schemas for new data marts and views
    # =====================================================================
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SUPPLIERS_MART}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_CATEGORIES_MART}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_DISABILITY_MART}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_DQ_VIEWS}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_LINEAGE_VIEWS}")

    # =====================================================================
    # 2. Create partitions for fact tables (2024, 2025, 2026)
    #    This is an example; in production, this would be managed
    #    by an automated process.
    # =====================================================================
    for year in [2024, 2025, 2026]:
        for fact_table in [
            "fact_licitacion_partitioned",
            "fact_oferta_partitioned",
            "fact_adjudicacion_partitioned",
            "fact_orden_compra_partitioned",
        ]:
            op.execute(f"""
                CREATE TABLE IF NOT EXISTS {_DW}.{fact_table}_{year}
                PARTITION OF {_DW}.{fact_table}
                FOR VALUES FROM ('{year}-01-01') TO ('{year+1}-01-01');
            """)

    # =====================================================================
    # 3. Create missing materialized view from Iteration 3
    # =====================================================================
    op.execute(f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {_ANALYTICS}.mv_market_monthly AS
        SELECT
            DATE_TRUNC('month', fl.periodo)::date AS mes,
            COUNT(DISTINCT fl.licitacion_id) AS total_licitaciones,
            COUNT(DISTINCT fa.adjudicacion_id) AS total_adjudicaciones,
            COALESCE(SUM(fa.monto_adjudicado), 0) AS monto_total_adjudicado
        FROM {_DW}.fact_licitacion_partitioned fl
        LEFT JOIN {_DW}.fact_adjudicacion_partitioned fa ON fl.licitacion_id::integer = fa.licitacion_key
        GROUP BY DATE_TRUNC('month', fl.periodo)::date
        ORDER BY mes DESC;
    """)

    # =====================================================================
    # 4. Create views/marts for Iteration 4
    # =====================================================================
    op.execute(f"""
        CREATE OR REPLACE VIEW {_SUPPLIERS_MART}.v_supplier_performance AS
        SELECT
            p.razon_social,
            p.rut,
            COUNT(DISTINCT fa.adjudicacion_id) AS total_adjudicaciones,
            SUM(fa.monto_adjudicado) AS monto_total_adjudicado,
            AVG(fa.ratio_adjudicacion) AS ratio_adjudicacion_promedio,
            MAX(fa.periodo) AS ultima_adjudicacion
        FROM {_DW}.fact_adjudicacion_partitioned fa
        JOIN {_DW}.dim_proveedor p ON fa.proveedor_key = p.proveedor_key AND p.is_current
        GROUP BY p.razon_social, p.rut;
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW {_CATEGORIES_MART}.v_category_spending AS
        SELECT
            c.nombre AS categoria,
            c.codigo AS codigo_categoria,
            SUM(foc.monto_total) AS gasto_total_oc,
            COUNT(DISTINCT foc.orden_compra_id) AS numero_ordenes_compra,
            AVG(foc.monto_total) AS gasto_promedio_oc
        FROM {_DW}.fact_orden_compra_partitioned foc
        JOIN {_DW}.dim_categoria c ON foc.categoria_key = c.categoria_key
        GROUP BY c.nombre, c.codigo;
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW {_DISABILITY_MART}.v_disability_contracts AS
        SELECT
            l.source_id as licitacion_id,
            l.nombre,
            l.descripcion,
            fa.monto_adjudicado,
            p.razon_social as proveedor,
            o.nombre as organismo,
            fa.periodo
        FROM {_DW}.fact_adjudicacion_partitioned fa
        JOIN core.licitacion l ON fa.licitacion_key = l.id
        JOIN {_DW}.dim_proveedor p ON fa.proveedor_key = p.proveedor_key AND p.is_current
        JOIN {_DW}.dim_organismo o ON fa.organismo_key = o.organismo_key AND o.is_current
        WHERE l.nombre ILIKE '%discapacidad%'
           OR l.descripcion ILIKE '%discapacidad%'
           OR l.nombre ILIKE '%inclusión%'
           OR l.descripcion ILIKE '%inclusión%';
    """)

    # =====================================================================
    # 5. Create Data Quality and Lineage views for Iteration 4
    # =====================================================================
    op.execute(f"""
        CREATE OR REPLACE VIEW {_DQ_VIEWS}.v_facts_missing_keys AS
        SELECT 'fact_licitacion' as fact_table, COUNT(*) as missing_count
        FROM {_DW}.fact_licitacion_partitioned
        WHERE fecha_key IS NULL OR organismo_key IS NULL OR categoria_key IS NULL
        UNION ALL
        SELECT 'fact_oferta' as fact_table, COUNT(*) as missing_count
        FROM {_DW}.fact_oferta_partitioned
        WHERE fecha_key IS NULL OR licitacion_key IS NULL OR proveedor_key IS NULL
        UNION ALL
        SELECT 'fact_adjudicacion' as fact_table, COUNT(*) as missing_count
        FROM {_DW}.fact_adjudicacion_partitioned
        WHERE fecha_key IS NULL OR licitacion_key IS NULL OR proveedor_key IS NULL OR organismo_key IS NULL
        UNION ALL
        SELECT 'fact_orden_compra' as fact_table, COUNT(*) as missing_count
        FROM {_DW}.fact_orden_compra_partitioned
        WHERE fecha_key IS NULL OR organismo_key IS NULL OR proveedor_key IS NULL;
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW {_LINEAGE_VIEWS}.v_marts_to_dw AS
        SELECT
            '{_SUPPLIERS_MART}.v_supplier_performance' as mart_view,
            'dw.fact_adjudicacion_partitioned, dw.dim_proveedor' as dw_dependencies
        UNION ALL
        SELECT
            '{_CATEGORIES_MART}.v_category_spending' as mart_view,
            'dw.fact_orden_compra_partitioned, dw.dim_categoria' as dw_dependencies
        UNION ALL
        SELECT
            '{_DISABILITY_MART}.v_disability_contracts' as mart_view,
            'dw.fact_adjudicacion_partitioned, core.licitacion, dw.dim_proveedor, dw.dim_organismo' as dw_dependencies
        UNION ALL
        SELECT
            '{_ANALYTICS}.mv_market_monthly' as mart_view,
            'dw.fact_licitacion_partitioned, dw.fact_adjudicacion_partitioned' as dw_dependencies;
    """)


def downgrade() -> None:
    # Drop views
    op.execute(f"DROP VIEW IF EXISTS {_LINEAGE_VIEWS}.v_marts_to_dw")
    op.execute(f"DROP VIEW IF EXISTS {_DQ_VIEWS}.v_facts_missing_keys")
    op.execute(f"DROP VIEW IF EXISTS {_DISABILITY_MART}.v_disability_contracts")
    op.execute(f"DROP VIEW IF EXISTS {_CATEGORIES_MART}.v_category_spending")
    op.execute(f"DROP VIEW IF EXISTS {_SUPPLIERS_MART}.v_supplier_performance")

    # Drop materialized view
    op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {_ANALYTICS}.mv_market_monthly")

    # Drop partitions
    for year in [2024, 2025, 2026]:
        for fact_table in [
            "fact_licitacion_partitioned",
            "fact_oferta_partitioned",
            "fact_adjudicacion_partitioned",
            "fact_orden_compra_partitioned",
        ]:
            op.execute(f"DROP TABLE IF EXISTS {_DW}.{fact_table}_{year}")

    # Drop schemas
    op.execute(f"DROP SCHEMA IF EXISTS {_LINEAGE_VIEWS}")
    op.execute(f"DROP SCHEMA IF EXISTS {_DQ_VIEWS}")
    op.execute(f"DROP SCHEMA IF EXISTS {_DISABILITY_MART}")
    op.execute(f"DROP SCHEMA IF EXISTS {_CATEGORIES_MART}")
    op.execute(f"DROP SCHEMA IF EXISTS {_SUPPLIERS_MART}")
