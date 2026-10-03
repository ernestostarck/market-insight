"""create core canonical model (Fase 4 - Iteración 1)

Revision ID: 20260807_0004
Revises: 20260806_0003
Create Date: 2026-08-07

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260807_0004"
down_revision = "20260806_0003"
branch_labels = None
depends_on = None

_SCHEMA = "core"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")

    # ------------------------------------------------------------------
    # core.organismo
    # ------------------------------------------------------------------
    op.create_table(
        "organismo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("codigo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("tipo", sa.String(length=128), nullable=True),
        sa.Column("sector", sa.String(length=256), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("comuna", sa.String(length=128), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.proveedor
    # ------------------------------------------------------------------
    op.create_table(
        "proveedor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("rut", sa.String(length=12), nullable=True),
        sa.Column("razon_social", sa.String(length=512), nullable=True),
        sa.Column("nombre_fantasia", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("tipo", sa.String(length=64), nullable=True),
        sa.Column("estado", sa.String(length=64), nullable=True),
        sa.Column("categoria_economica", sa.String(length=256), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("comuna", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.categoria
    # ------------------------------------------------------------------
    op.create_table(
        "categoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("codigo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("categoria_padre", sa.String(length=64), nullable=True),
        sa.Column("nivel", sa.Integer(), nullable=True),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.producto
    # ------------------------------------------------------------------
    op.create_table(
        "producto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("codigo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("nombre_normalizado", sa.String(length=512), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("unidad", sa.String(length=64), nullable=True),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_id"], ["core.categoria.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.licitacion
    # ------------------------------------------------------------------
    op.create_table(
        "licitacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("codigo", sa.String(length=128), nullable=True),
        sa.Column("nombre", sa.String(length=1024), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=64), nullable=True),
        sa.Column("tipo", sa.String(length=64), nullable=True),
        sa.Column("organismo_id", sa.Integer(), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("fecha_publicacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_adjudicacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("monto_estimado", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=8), nullable=True, server_default="CLP"),
        sa.Column(
            "es_desierta", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "es_adjudicada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_id"], ["core.categoria.id"]),
        sa.ForeignKeyConstraint(["organismo_id"], ["core.organismo.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.licitacion_item
    # ------------------------------------------------------------------
    op.create_table(
        "licitacion_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=True),
        sa.Column("producto_id", sa.Integer(), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("codigo", sa.String(length=128), nullable=True),
        sa.Column("nombre", sa.String(length=1024), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=True),
        sa.Column("unidad", sa.String(length=64), nullable=True),
        sa.Column("precio_unitario", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=8), nullable=True, server_default="CLP"),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["categoria_id"], ["core.categoria.id"]),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["core.producto.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.oferta
    # ------------------------------------------------------------------
    op.create_table(
        "oferta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("licitacion_id", sa.Integer(), nullable=True),
        sa.Column("proveedor_id", sa.Integer(), nullable=True),
        sa.Column("monto", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=8), nullable=True, server_default="CLP"),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=64), nullable=True),
        sa.Column("posicion", sa.Integer(), nullable=True),
        sa.Column(
            "es_adjudicada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["core.proveedor.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.adjudicacion
    # ------------------------------------------------------------------
    op.create_table(
        "adjudicacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("licitacion_id", sa.Integer(), nullable=True),
        sa.Column("proveedor_id", sa.Integer(), nullable=True),
        sa.Column("organismo_id", sa.Integer(), nullable=True),
        sa.Column("oferta_id", sa.Integer(), nullable=True),
        sa.Column("monto_adjudicado", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_estimado", sa.Numeric(18, 2), nullable=True),
        sa.Column("ratio_adjudicacion", sa.Numeric(10, 4), nullable=True),
        sa.Column("cantidad_ofertas", sa.Integer(), nullable=True),
        sa.Column("fecha_adjudicacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=64), nullable=True),
        sa.Column(
            "quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"]),
        sa.ForeignKeyConstraint(["oferta_id"], ["core.oferta.id"]),
        sa.ForeignKeyConstraint(["organismo_id"], ["core.organismo.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["core.proveedor.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.orden_compra
    # ------------------------------------------------------------------
    op.create_table(
        "orden_compra",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("codigo", sa.String(length=128), nullable=True),
        sa.Column("licitacion_id", sa.Integer(), nullable=True),
        sa.Column("adjudicacion_id", sa.Integer(), nullable=True),
        sa.Column("organismo_id", sa.Integer(), nullable=True),
        sa.Column("proveedor_id", sa.Integer(), nullable=True),
        sa.Column("estado", sa.String(length=64), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_emision", sa.DateTime(timezone=True), nullable=True),
        sa.Column("monto_neto", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_iva", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=8), nullable=True, server_default="CLP"),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["adjudicacion_id"], ["core.adjudicacion.id"]),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"]),
        sa.ForeignKeyConstraint(["organismo_id"], ["core.organismo.id"]),
        sa.ForeignKeyConstraint(["proveedor_id"], ["core.proveedor.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.orden_compra_item
    # ------------------------------------------------------------------
    op.create_table(
        "orden_compra_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("orden_compra_id", sa.Integer(), nullable=True),
        sa.Column("producto_id", sa.Integer(), nullable=True),
        sa.Column("codigo", sa.String(length=128), nullable=True),
        sa.Column("nombre", sa.String(length=1024), nullable=True),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=True),
        sa.Column("unidad", sa.String(length=64), nullable=True),
        sa.Column("precio_unitario", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=8), nullable=True, server_default="CLP"),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["orden_compra_id"], ["core.orden_compra.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["core.producto.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # core.documento
    # ------------------------------------------------------------------
    op.create_table(
        "documento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column(
            "source_system",
            sa.String(length=64),
            nullable=False,
            server_default="mercado_publico",
        ),
        sa.Column("licitacion_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=64), nullable=True),
        sa.Column("nombre", sa.String(length=512), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("natural_key", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("natural_key"),
        schema=_SCHEMA,
    )

    # ---------------------------------------------------------------------------
    # Indexes
    # ---------------------------------------------------------------------------
    _indexes = [
        ("ix_core_organismo_source_id", "organismo", ["source_id"]),
        ("ix_core_organismo_codigo", "organismo", ["codigo"]),
        ("ix_core_organismo_nombre_normalizado", "organismo", ["nombre_normalizado"]),
        ("ix_core_proveedor_source_id", "proveedor", ["source_id"]),
        ("ix_core_proveedor_rut", "proveedor", ["rut"]),
        ("ix_core_proveedor_nombre_normalizado", "proveedor", ["nombre_normalizado"]),
        ("ix_core_proveedor_estado", "proveedor", ["estado"]),
        ("ix_core_categoria_source_id", "categoria", ["source_id"]),
        ("ix_core_categoria_codigo", "categoria", ["codigo"]),
        ("ix_core_categoria_nombre_normalizado", "categoria", ["nombre_normalizado"]),
        ("ix_core_producto_source_id", "producto", ["source_id"]),
        ("ix_core_producto_codigo", "producto", ["codigo"]),
        ("ix_core_producto_nombre_normalizado", "producto", ["nombre_normalizado"]),
        ("ix_core_producto_categoria_id", "producto", ["categoria_id"]),
        ("ix_core_licitacion_source_id", "licitacion", ["source_id"]),
        ("ix_core_licitacion_codigo", "licitacion", ["codigo"]),
        ("ix_core_licitacion_estado", "licitacion", ["estado"]),
        ("ix_core_licitacion_tipo", "licitacion", ["tipo"]),
        ("ix_core_licitacion_organismo_id", "licitacion", ["organismo_id"]),
        ("ix_core_licitacion_categoria_id", "licitacion", ["categoria_id"]),
        ("ix_core_licitacion_fecha_publicacion", "licitacion", ["fecha_publicacion"]),
        ("ix_core_licitacion_fecha_cierre", "licitacion", ["fecha_cierre"]),
        ("ix_core_licitacion_item_licitacion_id", "licitacion_item", ["licitacion_id"]),
        ("ix_core_licitacion_item_producto_id", "licitacion_item", ["producto_id"]),
        ("ix_core_licitacion_item_categoria_id", "licitacion_item", ["categoria_id"]),
        ("ix_core_licitacion_item_codigo", "licitacion_item", ["codigo"]),
        ("ix_core_oferta_source_id", "oferta", ["source_id"]),
        ("ix_core_oferta_licitacion_id", "oferta", ["licitacion_id"]),
        ("ix_core_oferta_proveedor_id", "oferta", ["proveedor_id"]),
        ("ix_core_oferta_estado", "oferta", ["estado"]),
        ("ix_core_adjudicacion_source_id", "adjudicacion", ["source_id"]),
        ("ix_core_adjudicacion_licitacion_id", "adjudicacion", ["licitacion_id"]),
        ("ix_core_adjudicacion_proveedor_id", "adjudicacion", ["proveedor_id"]),
        ("ix_core_adjudicacion_organismo_id", "adjudicacion", ["organismo_id"]),
        ("ix_core_adjudicacion_oferta_id", "adjudicacion", ["oferta_id"]),
        (
            "ix_core_adjudicacion_fecha_adjudicacion",
            "adjudicacion",
            ["fecha_adjudicacion"],
        ),
        ("ix_core_adjudicacion_estado", "adjudicacion", ["estado"]),
        ("ix_core_orden_compra_source_id", "orden_compra", ["source_id"]),
        ("ix_core_orden_compra_codigo", "orden_compra", ["codigo"]),
        ("ix_core_orden_compra_licitacion_id", "orden_compra", ["licitacion_id"]),
        ("ix_core_orden_compra_adjudicacion_id", "orden_compra", ["adjudicacion_id"]),
        ("ix_core_orden_compra_organismo_id", "orden_compra", ["organismo_id"]),
        ("ix_core_orden_compra_proveedor_id", "orden_compra", ["proveedor_id"]),
        ("ix_core_orden_compra_estado", "orden_compra", ["estado"]),
        ("ix_core_orden_compra_fecha_creacion", "orden_compra", ["fecha_creacion"]),
        ("ix_core_orden_compra_fecha_emision", "orden_compra", ["fecha_emision"]),
        (
            "ix_core_orden_compra_item_orden_compra_id",
            "orden_compra_item",
            ["orden_compra_id"],
        ),
        ("ix_core_orden_compra_item_producto_id", "orden_compra_item", ["producto_id"]),
        ("ix_core_orden_compra_item_codigo", "orden_compra_item", ["codigo"]),
        ("ix_core_documento_source_id", "documento", ["source_id"]),
        ("ix_core_documento_licitacion_id", "documento", ["licitacion_id"]),
        ("ix_core_documento_tipo", "documento", ["tipo"]),
    ]

    for index_name, table, columns in _indexes:
        op.create_index(
            index_name,
            table,
            columns,
            unique=False,
            schema=_SCHEMA,
        )

    # ---------------------------------------------------------------------------
    # Grants / ownership
    # ---------------------------------------------------------------------------
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
    _indexes = [
        ("ix_core_documento_tipo", "documento"),
        ("ix_core_documento_licitacion_id", "documento"),
        ("ix_core_documento_source_id", "documento"),
        ("ix_core_orden_compra_item_codigo", "orden_compra_item"),
        ("ix_core_orden_compra_item_producto_id", "orden_compra_item"),
        ("ix_core_orden_compra_item_orden_compra_id", "orden_compra_item"),
        ("ix_core_orden_compra_fecha_emision", "orden_compra"),
        ("ix_core_orden_compra_fecha_creacion", "orden_compra"),
        ("ix_core_orden_compra_estado", "orden_compra"),
        ("ix_core_orden_compra_proveedor_id", "orden_compra"),
        ("ix_core_orden_compra_organismo_id", "orden_compra"),
        ("ix_core_orden_compra_adjudicacion_id", "orden_compra"),
        ("ix_core_orden_compra_licitacion_id", "orden_compra"),
        ("ix_core_orden_compra_codigo", "orden_compra"),
        ("ix_core_orden_compra_source_id", "orden_compra"),
        ("ix_core_adjudicacion_estado", "adjudicacion"),
        ("ix_core_adjudicacion_fecha_adjudicacion", "adjudicacion"),
        ("ix_core_adjudicacion_oferta_id", "adjudicacion"),
        ("ix_core_adjudicacion_organismo_id", "adjudicacion"),
        ("ix_core_adjudicacion_proveedor_id", "adjudicacion"),
        ("ix_core_adjudicacion_licitacion_id", "adjudicacion"),
        ("ix_core_adjudicacion_source_id", "adjudicacion"),
        ("ix_core_oferta_estado", "oferta"),
        ("ix_core_oferta_proveedor_id", "oferta"),
        ("ix_core_oferta_licitacion_id", "oferta"),
        ("ix_core_oferta_source_id", "oferta"),
        ("ix_core_licitacion_item_codigo", "licitacion_item"),
        ("ix_core_licitacion_item_categoria_id", "licitacion_item"),
        ("ix_core_licitacion_item_producto_id", "licitacion_item"),
        ("ix_core_licitacion_item_licitacion_id", "licitacion_item"),
        ("ix_core_licitacion_fecha_cierre", "licitacion"),
        ("ix_core_licitacion_fecha_publicacion", "licitacion"),
        ("ix_core_licitacion_categoria_id", "licitacion"),
        ("ix_core_licitacion_organismo_id", "licitacion"),
        ("ix_core_licitacion_tipo", "licitacion"),
        ("ix_core_licitacion_estado", "licitacion"),
        ("ix_core_licitacion_codigo", "licitacion"),
        ("ix_core_licitacion_source_id", "licitacion"),
        ("ix_core_producto_categoria_id", "producto"),
        ("ix_core_producto_nombre_normalizado", "producto"),
        ("ix_core_producto_codigo", "producto"),
        ("ix_core_producto_source_id", "producto"),
        ("ix_core_categoria_nombre_normalizado", "categoria"),
        ("ix_core_categoria_codigo", "categoria"),
        ("ix_core_categoria_source_id", "categoria"),
        ("ix_core_proveedor_estado", "proveedor"),
        ("ix_core_proveedor_nombre_normalizado", "proveedor"),
        ("ix_core_proveedor_rut", "proveedor"),
        ("ix_core_proveedor_source_id", "proveedor"),
        ("ix_core_organismo_nombre_normalizado", "organismo"),
        ("ix_core_organismo_codigo", "organismo"),
        ("ix_core_organismo_source_id", "organismo"),
    ]

    for index_name, table in _indexes:
        op.drop_index(index_name, table_name=table, schema=_SCHEMA)

    for table in [
        "documento",
        "orden_compra_item",
        "orden_compra",
        "adjudicacion",
        "oferta",
        "licitacion_item",
        "licitacion",
        "producto",
        "categoria",
        "proveedor",
        "organismo",
    ]:
        op.drop_table(table, schema=_SCHEMA)
