"""add SCD2, partitioning, materialized views (Fase 4 - Iteración 3)

Revision ID: 20260807_0006
Revises: 20260807_0005
Create Date: 2026-08-07

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260807_0006"
down_revision = "20260807_0005"
branch_labels = None
depends_on = None

_DW = "dw"
_ANALYTICS = "analytics"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_ANALYTICS}")

    # =====================================================================
    # 1.a Add natural_key to SCD2 dimensions (dim_organismo, dim_proveedor)
    # =====================================================================
    op.execute(
        f"ALTER TABLE {_DW}.dim_organismo ADD COLUMN IF NOT EXISTS "
        f"natural_key VARCHAR(256)"
    )
    op.execute(
        f"ALTER TABLE {_DW}.dim_proveedor ADD COLUMN IF NOT EXISTS "
        f"natural_key VARCHAR(256)"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_dim_organismo_natural_key "
        f"ON {_DW}.dim_organismo (natural_key)"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_dim_proveedor_natural_key "
        f"ON {_DW}.dim_proveedor (natural_key)"
    )

    # =====================================================================
    # 1.b SCD Type 2 helpers (dim_organismo, dim_proveedor)
    # =====================================================================
    op.execute(f"""
        CREATE OR REPLACE FUNCTION {_DW}.scd2_close_previous()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE {_DW}.dim_organismo
               SET valid_to = NEW.valid_from, is_current = FALSE
             WHERE natural_key = NEW.natural_key
               AND is_current = TRUE
               AND organismo_key <> NEW.organismo_key;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute(f"""
        CREATE OR REPLACE FUNCTION {_DW}.scd2_close_previous_proveedor()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE {_DW}.dim_proveedor
               SET valid_to = NEW.valid_from, is_current = FALSE
             WHERE natural_key = NEW.natural_key
               AND is_current = TRUE
               AND proveedor_key <> NEW.proveedor_key;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # =====================================================================
    # 2. Partitioned fact tables (by month range on fecha_key-based date)
    #    We use a created_at_part column for partition key to avoid
    #    coupling with nullable fecha PKs.
    # =====================================================================
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {_DW}.fact_licitacion_partitioned (
            id BIGINT NOT NULL,
            licitacion_id VARCHAR(128),
            fecha_key INTEGER,
            organismo_key INTEGER,
            categoria_key INTEGER,
            tipo_licitacion_key INTEGER,
            estado_key INTEGER,
            monto_estimado NUMERIC(18,2),
            cantidad_items INTEGER,
            cantidad_ofertas INTEGER,
            es_adjudicada BOOLEAN NOT NULL DEFAULT FALSE,
            es_desierta BOOLEAN NOT NULL DEFAULT FALSE,
            fuente VARCHAR(64),
            periodo DATE NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, periodo)
        ) PARTITION BY RANGE (periodo);
    """)

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {_DW}.fact_oferta_partitioned (
            id BIGINT NOT NULL,
            oferta_id VARCHAR(128),
            fecha_key INTEGER,
            licitacion_key INTEGER,
            proveedor_key INTEGER,
            categoria_key INTEGER,
            monto_oferta NUMERIC(18,2),
            posicion INTEGER,
            es_adjudicada BOOLEAN NOT NULL DEFAULT FALSE,
            fuente VARCHAR(64),
            periodo DATE NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, periodo)
        ) PARTITION BY RANGE (periodo);
    """)

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {_DW}.fact_adjudicacion_partitioned (
            id BIGINT NOT NULL,
            adjudicacion_id VARCHAR(128),
            fecha_key INTEGER,
            licitacion_key INTEGER,
            proveedor_key INTEGER,
            organismo_key INTEGER,
            categoria_key INTEGER,
            monto_adjudicado NUMERIC(18,2),
            monto_estimado NUMERIC(18,2),
            ratio_adjudicacion NUMERIC(10,4),
            cantidad_items INTEGER,
            cantidad_ofertas INTEGER,
            fuente VARCHAR(64),
            periodo DATE NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, periodo)
        ) PARTITION BY RANGE (periodo);
    """)

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {_DW}.fact_orden_compra_partitioned (
            id BIGINT NOT NULL,
            orden_compra_id VARCHAR(128),
            fecha_key INTEGER,
            organismo_key INTEGER,
            proveedor_key INTEGER,
            categoria_key INTEGER,
            monto_neto NUMERIC(18,2),
            monto_iva NUMERIC(18,2),
            monto_total NUMERIC(18,2),
            cantidad_items INTEGER,
            fuente VARCHAR(64),
            periodo DATE NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, periodo)
        ) PARTITION BY RANGE (periodo);
    """)

    # =====================================================================
    # 3. Materialized views (analytics)
    # =====================================================================
    op.execute(f"""
        CREATE MATERIALIZED VIEW {_ANALYTICS}.mv_licitaciones_por_organismo_mes AS
        SELECT
            o.nombre                          AS organismo,
            DATE_TRUNC('month', l.fecha_publicacion)::date AS mes,
            COUNT(*)                          AS total_licitaciones,
            COUNT(*) FILTER (WHERE l.es_adjudicada) AS adjudicadas,
            COUNT(*) FILTER (WHERE l.es_desierta)  AS desiertas,
            COALESCE(SUM(l.monto_estimado), 0)     AS monto_estimado_total
        FROM {_DW}.fact_licitacion_partitioned fl
        JOIN core.organismo o ON o.id = fl.organismo_key
        JOIN core.licitacion l ON l.id = fl.licitacion_id::integer
        GROUP BY o.nombre, DATE_TRUNC('month', l.fecha_publicacion)::date
    """)

    op.execute(f"""
        CREATE MATERIALIZED VIEW {_ANALYTICS}.mv_adjudicaciones_por_proveedor AS
        SELECT
            p.razon_social                          AS proveedor,
            COUNT(*)                                AS total_adjudicaciones,
            COALESCE(SUM(a.monto_adjudicado), 0)    AS monto_total_adjudicado,
            AVG(a.ratio_adjudicacion)               AS ratio_promedio
        FROM {_DW}.fact_adjudicacion_partitioned fa
        JOIN core.proveedor p ON p.id = fa.proveedor_key
        JOIN core.adjudicacion a ON a.id = fa.adjudicacion_id::integer
        GROUP BY p.razon_social
    """)

    op.execute(f"""
        CREATE MATERIALIZED VIEW {_ANALYTICS}.mv_tasa_adjudicacion_mensual AS
        SELECT
            DATE_TRUNC('month', l.fecha_publicacion)::date AS mes,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE l.es_adjudicada) AS adjudicadas,
            ROUND(
                COUNT(*) FILTER (WHERE l.es_adjudicada)::numeric
                / NULLIF(COUNT(*), 0), 4
            ) AS tasa_adjudicacion
        FROM {_DW}.fact_licitacion_partitioned fl
        JOIN core.licitacion l ON l.id = fl.licitacion_id::integer
        GROUP BY DATE_TRUNC('month', l.fecha_publicacion)::date
    """)

    # =====================================================================
    # 4. Additional indexes for partitioned facts
    # =====================================================================
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_fact_licit_part_org "
        f"ON {_DW}.fact_licitacion_partitioned (organismo_key, periodo)"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_fact_licit_part_estado "
        f"ON {_DW}.fact_licitacion_partitioned (estado_key, periodo)"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_fact_adj_part_prov "
        f"ON {_DW}.fact_adjudicacion_partitioned (proveedor_key, periodo)"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_fact_adj_part_org "
        f"ON {_DW}.fact_adjudicacion_partitioned (organismo_key, periodo)"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_dw_fact_oc_part_prov "
        f"ON {_DW}.fact_orden_compra_partitioned (proveedor_key, periodo)"
    )

    # =====================================================================
    # 5. Grants
    # =====================================================================
    op.execute(
        f"GRANT USAGE ON SCHEMA {_ANALYTICS} TO market_insight_admin, "
        f"market_insight_app, market_insight_readonly"
    )
    op.execute(
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {_ANALYTICS} TO "
        f"market_insight_app, market_insight_readonly"
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {_DW} "
        f"TO market_insight_app"
    )


def downgrade() -> None:
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {_ANALYTICS}.mv_tasa_adjudicacion_mensual"
    )
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {_ANALYTICS}.mv_adjudicaciones_por_proveedor"
    )
    op.execute(
        f"DROP MATERIALIZED VIEW IF EXISTS {_ANALYTICS}.mv_licitaciones_por_organismo_mes"
    )

    op.execute(f"DROP TABLE IF EXISTS {_DW}.fact_orden_compra_partitioned CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {_DW}.fact_adjudicacion_partitioned CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {_DW}.fact_oferta_partitioned CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {_DW}.fact_licitacion_partitioned CASCADE")

    op.execute(f"DROP FUNCTION IF EXISTS {_DW}.scd2_close_previous_proveedor()")
    op.execute(f"DROP FUNCTION IF EXISTS {_DW}.scd2_close_previous()")
