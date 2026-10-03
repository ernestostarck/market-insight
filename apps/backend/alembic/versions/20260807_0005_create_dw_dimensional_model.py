"""create dw dimensional model (Fase 4 - Iteración 2)

Revision ID: 20260807_0005
Revises: 20260807_0004
Create Date: 2026-08-07

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260807_0005"
down_revision = "20260807_0004"
branch_labels = None
depends_on = None

_SCHEMA = "dw"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------
    op.create_table(
        "dim_fecha",
        sa.Column("fecha_key", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("dia", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("semana", sa.Integer(), nullable=False),
        sa.Column("nombre_mes", sa.String(length=32), nullable=True),
        sa.Column("nombre_dia", sa.String(length=32), nullable=True),
        sa.Column("es_fin_de_semana", sa.Boolean(), nullable=False),
        sa.Column("es_feriado", sa.Boolean(), nullable=False),
        sa.Column("anio_mes", sa.String(length=7), nullable=False),
        sa.PrimaryKeyConstraint("fecha_key"),
        sa.UniqueConstraint("fecha"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_organismo",
        sa.Column("organismo_key", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("codigo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("tipo", sa.String(length=128), nullable=True),
        sa.Column("sector", sa.String(length=256), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("comuna", sa.String(length=128), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("organismo_key"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_proveedor",
        sa.Column("proveedor_key", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("rut", sa.String(length=12), nullable=True),
        sa.Column("razon_social", sa.String(length=512), nullable=True),
        sa.Column("nombre_fantasia", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("tipo", sa.String(length=64), nullable=True),
        sa.Column("estado", sa.String(length=64), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("comuna", sa.String(length=128), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("proveedor_key"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_categoria",
        sa.Column("categoria_key", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("codigo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("categoria_padre", sa.String(length=64), nullable=True),
        sa.Column("nivel", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("categoria_key"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_producto",
        sa.Column("producto_key", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("codigo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("categoria_key", sa.Integer(), nullable=True),
        sa.Column("unidad", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("producto_key"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_ubicacion",
        sa.Column("ubicacion_key", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("comuna", sa.String(length=128), nullable=True),
        sa.Column("provincia", sa.String(length=128), nullable=True),
        sa.Column("latitud", sa.Numeric(10, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(10, 6), nullable=True),
        sa.PrimaryKeyConstraint("ubicacion_key"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_estado_licitacion",
        sa.Column("estado_key", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=64), nullable=False),
        sa.Column("nombre", sa.String(length=256), nullable=True),
        sa.Column("descripcion", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("estado_key"),
        sa.UniqueConstraint("codigo"),
        schema=_SCHEMA,
    )

    op.create_table(
        "dim_tipo_licitacion",
        sa.Column("tipo_key", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=64), nullable=False),
        sa.Column("nombre", sa.String(length=256), nullable=True),
        sa.Column("descripcion", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("tipo_key"),
        sa.UniqueConstraint("codigo"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # Facts
    # ------------------------------------------------------------------
    op.create_table(
        "fact_licitacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("licitacion_id", sa.String(length=128), nullable=True),
        sa.Column("fecha_key", sa.Integer(), nullable=True),
        sa.Column("organismo_key", sa.Integer(), nullable=True),
        sa.Column("categoria_key", sa.Integer(), nullable=True),
        sa.Column("tipo_licitacion_key", sa.Integer(), nullable=True),
        sa.Column("estado_key", sa.Integer(), nullable=True),
        sa.Column("monto_estimado", sa.Numeric(18, 2), nullable=True),
        sa.Column("cantidad_items", sa.Integer(), nullable=True),
        sa.Column("cantidad_ofertas", sa.Integer(), nullable=True),
        sa.Column("es_adjudicada", sa.Boolean(), nullable=False),
        sa.Column("es_desierta", sa.Boolean(), nullable=False),
        sa.Column("fuente", sa.String(length=64), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_key"], ["dw.dim_categoria.categoria_key"]),
        sa.ForeignKeyConstraint(
            ["estado_key"], ["dw.dim_estado_licitacion.estado_key"]
        ),
        sa.ForeignKeyConstraint(["fecha_key"], ["dw.dim_fecha.fecha_key"]),
        sa.ForeignKeyConstraint(["organismo_key"], ["dw.dim_organismo.organismo_key"]),
        sa.ForeignKeyConstraint(
            ["tipo_licitacion_key"], ["dw.dim_tipo_licitacion.tipo_key"]
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    op.create_table(
        "fact_oferta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oferta_id", sa.String(length=128), nullable=True),
        sa.Column("fecha_key", sa.Integer(), nullable=True),
        sa.Column("licitacion_key", sa.Integer(), nullable=True),
        sa.Column("proveedor_key", sa.Integer(), nullable=True),
        sa.Column("categoria_key", sa.Integer(), nullable=True),
        sa.Column("monto_oferta", sa.Numeric(18, 2), nullable=True),
        sa.Column("posicion", sa.Integer(), nullable=True),
        sa.Column("es_adjudicada", sa.Boolean(), nullable=False),
        sa.Column("fuente", sa.String(length=64), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_key"], ["dw.dim_categoria.categoria_key"]),
        sa.ForeignKeyConstraint(["fecha_key"], ["dw.dim_fecha.fecha_key"]),
        sa.ForeignKeyConstraint(["proveedor_key"], ["dw.dim_proveedor.proveedor_key"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    op.create_table(
        "fact_adjudicacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adjudicacion_id", sa.String(length=128), nullable=True),
        sa.Column("fecha_key", sa.Integer(), nullable=True),
        sa.Column("licitacion_key", sa.Integer(), nullable=True),
        sa.Column("proveedor_key", sa.Integer(), nullable=True),
        sa.Column("organismo_key", sa.Integer(), nullable=True),
        sa.Column("categoria_key", sa.Integer(), nullable=True),
        sa.Column("monto_adjudicado", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_estimado", sa.Numeric(18, 2), nullable=True),
        sa.Column("ratio_adjudicacion", sa.Numeric(10, 4), nullable=True),
        sa.Column("cantidad_items", sa.Integer(), nullable=True),
        sa.Column("cantidad_ofertas", sa.Integer(), nullable=True),
        sa.Column("fuente", sa.String(length=64), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_key"], ["dw.dim_categoria.categoria_key"]),
        sa.ForeignKeyConstraint(["fecha_key"], ["dw.dim_fecha.fecha_key"]),
        sa.ForeignKeyConstraint(["organismo_key"], ["dw.dim_organismo.organismo_key"]),
        sa.ForeignKeyConstraint(["proveedor_key"], ["dw.dim_proveedor.proveedor_key"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    op.create_table(
        "fact_orden_compra",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("orden_compra_id", sa.String(length=128), nullable=True),
        sa.Column("fecha_key", sa.Integer(), nullable=True),
        sa.Column("organismo_key", sa.Integer(), nullable=True),
        sa.Column("proveedor_key", sa.Integer(), nullable=True),
        sa.Column("categoria_key", sa.Integer(), nullable=True),
        sa.Column("monto_neto", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_iva", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("cantidad_items", sa.Integer(), nullable=True),
        sa.Column("fuente", sa.String(length=64), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_key"], ["dw.dim_categoria.categoria_key"]),
        sa.ForeignKeyConstraint(["fecha_key"], ["dw.dim_fecha.fecha_key"]),
        sa.ForeignKeyConstraint(["organismo_key"], ["dw.dim_organismo.organismo_key"]),
        sa.ForeignKeyConstraint(["proveedor_key"], ["dw.dim_proveedor.proveedor_key"]),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    _dim_indexes = [
        ("ix_dw_dim_fecha_fecha", "dim_fecha", ["fecha"]),
        ("ix_dw_dim_fecha_anio", "dim_fecha", ["anio"]),
        ("ix_dw_dim_fecha_anio_mes", "dim_fecha", ["anio_mes"]),
        ("ix_dw_dim_organismo_source_id", "dim_organismo", ["source_id"]),
        ("ix_dw_dim_organismo_codigo", "dim_organismo", ["codigo"]),
        ("ix_dw_dim_organismo_nombre_norm", "dim_organismo", ["nombre_normalizado"]),
        ("ix_dw_dim_organismo_is_current", "dim_organismo", ["is_current"]),
        ("ix_dw_dim_proveedor_source_id", "dim_proveedor", ["source_id"]),
        ("ix_dw_dim_proveedor_rut", "dim_proveedor", ["rut"]),
        ("ix_dw_dim_proveedor_nombre_norm", "dim_proveedor", ["nombre_normalizado"]),
        ("ix_dw_dim_proveedor_is_current", "dim_proveedor", ["is_current"]),
        ("ix_dw_dim_categoria_source_id", "dim_categoria", ["source_id"]),
        ("ix_dw_dim_categoria_codigo", "dim_categoria", ["codigo"]),
        ("ix_dw_dim_categoria_nombre_norm", "dim_categoria", ["nombre_normalizado"]),
        ("ix_dw_dim_producto_source_id", "dim_producto", ["source_id"]),
        ("ix_dw_dim_producto_codigo", "dim_producto", ["codigo"]),
        ("ix_dw_dim_producto_nombre_norm", "dim_producto", ["nombre_normalizado"]),
        ("ix_dw_dim_producto_categoria_key", "dim_producto", ["categoria_key"]),
        ("ix_dw_dim_ubicacion_region", "dim_ubicacion", ["region"]),
        ("ix_dw_dim_ubicacion_comuna", "dim_ubicacion", ["comuna"]),
        ("ix_dw_dim_estado_codigo", "dim_estado_licitacion", ["codigo"]),
        ("ix_dw_dim_tipo_codigo", "dim_tipo_licitacion", ["codigo"]),
    ]
    for index_name, table, columns in _dim_indexes:
        op.create_index(index_name, table, columns, unique=False, schema=_SCHEMA)

    _fact_indexes = [
        ("ix_dw_fact_licitacion_id", "fact_licitacion", ["id"]),
        ("ix_dw_fact_licitacion_lic_id", "fact_licitacion", ["licitacion_id"]),
        ("ix_dw_fact_licitacion_fecha_key", "fact_licitacion", ["fecha_key"]),
        ("ix_dw_fact_licitacion_org_key", "fact_licitacion", ["organismo_key"]),
        ("ix_dw_fact_licitacion_cat_key", "fact_licitacion", ["categoria_key"]),
        ("ix_dw_fact_licitacion_tipo_key", "fact_licitacion", ["tipo_licitacion_key"]),
        ("ix_dw_fact_licitacion_estado_key", "fact_licitacion", ["estado_key"]),
        ("ix_dw_fact_oferta_id", "fact_oferta", ["id"]),
        ("ix_dw_fact_oferta_oferta_id", "fact_oferta", ["oferta_id"]),
        ("ix_dw_fact_oferta_fecha_key", "fact_oferta", ["fecha_key"]),
        ("ix_dw_fact_oferta_lic_key", "fact_oferta", ["licitacion_key"]),
        ("ix_dw_fact_oferta_prov_key", "fact_oferta", ["proveedor_key"]),
        ("ix_dw_fact_oferta_cat_key", "fact_oferta", ["categoria_key"]),
        ("ix_dw_fact_adjudicacion_id", "fact_adjudicacion", ["id"]),
        ("ix_dw_fact_adjudicacion_adj_id", "fact_adjudicacion", ["adjudicacion_id"]),
        ("ix_dw_fact_adjudicacion_fecha_key", "fact_adjudicacion", ["fecha_key"]),
        ("ix_dw_fact_adjudicacion_lic_key", "fact_adjudicacion", ["licitacion_key"]),
        ("ix_dw_fact_adjudicacion_prov_key", "fact_adjudicacion", ["proveedor_key"]),
        ("ix_dw_fact_adjudicacion_org_key", "fact_adjudicacion", ["organismo_key"]),
        ("ix_dw_fact_adjudicacion_cat_key", "fact_adjudicacion", ["categoria_key"]),
        ("ix_dw_fact_orden_compra_id", "fact_orden_compra", ["id"]),
        ("ix_dw_fact_orden_oc_id", "fact_orden_compra", ["orden_compra_id"]),
        ("ix_dw_fact_orden_fecha_key", "fact_orden_compra", ["fecha_key"]),
        ("ix_dw_fact_orden_org_key", "fact_orden_compra", ["organismo_key"]),
        ("ix_dw_fact_orden_prov_key", "fact_orden_compra", ["proveedor_key"]),
        ("ix_dw_fact_orden_cat_key", "fact_orden_compra", ["categoria_key"]),
    ]
    for index_name, table, columns in _fact_indexes:
        op.create_index(index_name, table, columns, unique=False, schema=_SCHEMA)

    # ------------------------------------------------------------------
    # Grants / ownership
    # ------------------------------------------------------------------
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {_SCHEMA} TO market_insight_app"
    )
    op.execute(
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {_SCHEMA} TO market_insight_readonly"
    )
    op.execute(
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {_SCHEMA} TO market_insight_admin, market_insight_app"
    )


def downgrade() -> None:
    for table in [
        "fact_orden_compra",
        "fact_adjudicacion",
        "fact_oferta",
        "fact_licitacion",
        "dim_tipo_licitacion",
        "dim_estado_licitacion",
        "dim_ubicacion",
        "dim_producto",
        "dim_categoria",
        "dim_proveedor",
        "dim_organismo",
        "dim_fecha",
    ]:
        op.drop_table(table, schema=_SCHEMA)
