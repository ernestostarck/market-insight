from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.etl.loading.dedup import ExistingRecordLookup, classify_batch
from app.etl.models import IngestionRunContext, LoadResult, TransformedRecord
from app.etl.transformation.keys import natural_key
from app.integrations.chilecompra.models import LicitacionDetalleItem

logger = logging.getLogger(__name__)

_LICITACION_COLUMNS: dict[str, str] = {
    "codigo": "codigo",
    "nombre": "nombre",
    "descripcion": "descripcion",
    "estado": "estado",
    "fecha_publicacion": "fecha_publicacion",
    "fecha_cierre": "fecha_cierre",
}


class CoreLicitacionLoader:
    """Load transformed licitacion records into `core.licitacion`.

    Same Core (Connection + text()) style as PostgresRecordLoader — kept
    consistent so it's testable the same way (fake connection stub), and
    because core.licitacion is the canonical, Alembic-migrated table the rest
    of the project reads from (unlike PostgresRecordLoader's procurement.*
    target, which nothing else in the app uses).
    """

    def __init__(self, connection_factory: Callable[[], Connection]) -> None:
        self._connection_factory = connection_factory

    def load(self, run: IngestionRunContext, records: list[TransformedRecord]) -> LoadResult:
        result = LoadResult()
        if not records:
            return result

        connection = self._connection_factory()
        try:
            buckets = classify_batch(records, self._existing_hash_lookup(connection))

            for record in buckets["insert"]:
                self._upsert(connection, record)
                result.inserted += 1
            for record in buckets["update"]:
                self._upsert(connection, record)
                result.updated += 1
            result.unchanged = len(buckets["unchanged"])
            connection.commit()
        except Exception:
            logger.exception("core.licitacion load failed for run=%s", run.ingestion_run_id)
            result.failed += len(records)
            connection.rollback()
            raise
        finally:
            connection.close()

        return result

    def _existing_hash_lookup(self, connection: Connection) -> ExistingRecordLookup:
        def lookup(entity: str, natural_key_value: str) -> str | None:
            if entity != "licitacion":
                return None
            row = connection.execute(
                text("SELECT payload_hash FROM core.licitacion WHERE natural_key = :natural_key"),
                {"natural_key": natural_key_value},
            ).first()
            return None if row is None else str(row[0])

        return lookup

    def _upsert(self, connection: Connection, record: TransformedRecord) -> None:
        organismo_id = self._resolve_organismo(connection, record.payload)

        columns = {
            column: record.payload[field]
            for field, column in _LICITACION_COLUMNS.items()
            if record.payload.get(field) is not None
        }
        if organismo_id is not None:
            columns["organismo_id"] = organismo_id

        params: dict[str, Any] = {
            **columns,
            "source_id": record.source_id,
            "natural_key": record.natural_key,
            "payload_hash": record.payload_hash,
        }
        insert_columns = ["source_id", "natural_key", "payload_hash", *columns.keys()]
        insert_values = [f":{column}" for column in insert_columns]
        update_assignments = ", ".join(
            f"{column} = :{column}" for column in ("payload_hash", *columns.keys())
        )

        connection.execute(
            text(
                f"INSERT INTO core.licitacion ({', '.join(insert_columns)}) "
                f"VALUES ({', '.join(insert_values)}) "
                f"ON CONFLICT (natural_key) DO UPDATE SET {update_assignments}, updated_at = now()"
            ),
            params,
        )

    def _resolve_organismo(self, connection: Connection, payload: dict[str, Any]) -> int | None:
        codigo = payload.get("agency_code")
        nombre = payload.get("agency_name")
        if not codigo:
            return None

        row = connection.execute(
            text("SELECT id FROM core.organismo WHERE codigo = :codigo"), {"codigo": codigo}
        ).first()
        if row is not None:
            return int(row[0])

        inserted = connection.execute(
            text(
                "INSERT INTO core.organismo (codigo, nombre, natural_key) "
                "VALUES (:codigo, :nombre, :natural_key) RETURNING id"
            ),
            {"codigo": codigo, "nombre": nombre, "natural_key": natural_key("organismo", codigo)},
        ).first()
        return int(inserted[0])


class CoreLicitacionItemLoader:
    """Upsert Items.Listado[] rows (from the licitacion detail endpoint) into
    `core.licitacion_item`. Not a RecordLoader: items are a 1-to-N collection
    per licitacion, not one entity per record.

    Each item carries ChileCompra's own rubro classification (`CodigoCategoria`/
    `Categoria`, parsed into `LicitacionDetalleItem.codigo_categoria`/`.categoria`)
    — this is where it gets resolved into `core.categoria` and linked, both per
    item and, as the item's most common category, on the licitacion itself.
    """

    def __init__(self, connection_factory: Callable[[], Connection]) -> None:
        self._connection_factory = connection_factory

    def upsert_items(
        self,
        connection: Connection,
        *,
        licitacion_codigo: str,
        items: list[LicitacionDetalleItem],
    ) -> int:
        if not items:
            return 0

        row = connection.execute(
            text("SELECT id FROM core.licitacion WHERE codigo = :codigo"),
            {"codigo": licitacion_codigo},
        ).first()
        if row is None:
            logger.warning("Skipping items for unknown licitacion codigo=%s", licitacion_codigo)
            return 0
        licitacion_id = int(row[0])

        upserted = 0
        item_categoria_ids: list[int] = []
        for item in items:
            categoria_id = self._resolve_categoria(connection, item.codigo_categoria, item.categoria)
            if categoria_id is not None:
                item_categoria_ids.append(categoria_id)

            connection.execute(
                text(
                    "INSERT INTO core.licitacion_item "
                    "(licitacion_id, codigo, nombre, descripcion, cantidad, unidad, categoria_id, natural_key) "
                    "VALUES (:licitacion_id, :codigo, :nombre, :descripcion, :cantidad, :unidad, :categoria_id, :natural_key) "
                    "ON CONFLICT (natural_key) DO UPDATE SET "
                    "codigo = :codigo, nombre = :nombre, descripcion = :descripcion, "
                    "cantidad = :cantidad, unidad = :unidad, categoria_id = :categoria_id, updated_at = now()"
                ),
                {
                    "licitacion_id": licitacion_id,
                    "codigo": str(item.codigo_producto) if item.codigo_producto is not None else None,
                    "nombre": item.nombre_producto,
                    "descripcion": item.descripcion,
                    "cantidad": item.cantidad,
                    "unidad": item.unidad_medida,
                    "categoria_id": categoria_id,
                    "natural_key": natural_key("licitacion_item", f"{licitacion_codigo}:{item.correlativo}"),
                },
            )
            upserted += 1

        if item_categoria_ids:
            dominant_categoria_id = Counter(item_categoria_ids).most_common(1)[0][0]
            connection.execute(
                text(
                    "UPDATE core.licitacion SET categoria_id = :categoria_id, updated_at = now() "
                    "WHERE codigo = :codigo"
                ),
                {"categoria_id": dominant_categoria_id, "codigo": licitacion_codigo},
            )

        return upserted

    def _resolve_categoria(
        self, connection: Connection, codigo: str | int | None, nombre: str | None
    ) -> int | None:
        """Get-or-create `core.categoria` by ChileCompra's own rubro code, same
        get-or-create shape as `CoreLicitacionLoader._resolve_organismo`."""
        if codigo is None:
            return None
        codigo_str = str(codigo)

        row = connection.execute(
            text("SELECT id FROM core.categoria WHERE codigo = :codigo"), {"codigo": codigo_str}
        ).first()
        if row is not None:
            return int(row[0])

        inserted = connection.execute(
            text(
                "INSERT INTO core.categoria (codigo, nombre, natural_key) "
                "VALUES (:codigo, :nombre, :natural_key) RETURNING id"
            ),
            {
                "codigo": codigo_str, "nombre": nombre,
                "natural_key": natural_key("categoria", codigo_str),
            },
        ).first()
        return int(inserted[0])


class CoreAdjudicacionLoader:
    """Load real awards into `core.adjudicacion`, resolving/creating the
    winning `core.proveedor`.

    The real proveedor/monto live per item, nested under each
    `Items.Listado[].Adjudicacion` object in the licitacion detail payload
    (por_codigo) — NOT in the separate `/adjudicaciones.json` resource, which
    only reports status changes (codigo/estado), no proveedor or monto (found
    by calling it against the real API — every field but estado came back
    null). So this loader takes `LicitacionDetalleItem`s (already fetched by
    app/etl/enrichment/licitacion_detail.py for categoria enrichment) rather
    than a `NormalizedAdjudicacion` from that endpoint.
    """

    def __init__(self, connection_factory: Callable[[], Connection]) -> None:
        self._connection_factory = connection_factory

    def upsert_from_items(
        self,
        connection: Connection,
        *,
        licitacion_codigo: str,
        monto_estimado: float | None,
        fecha_adjudicacion: Any,
        numero_oferentes: int | None,
        items: list[Any],
    ) -> int:
        """Aggregates items by winning proveedor (a multi-lot award becomes
        one core.adjudicacion row per proveedor, not per item) and upserts.
        Returns 0 (no-op) if the licitacion isn't tracked, or none of its
        items report a real proveedor_rut yet (not every closed tender's
        detail has award data populated by ChileCompra)."""
        row = connection.execute(
            text("SELECT id, organismo_id FROM core.licitacion WHERE codigo = :codigo"),
            {"codigo": licitacion_codigo},
        ).first()
        if row is None:
            return 0
        licitacion_id, organismo_id = int(row[0]), row[1]

        by_proveedor: dict[str, dict[str, Any]] = {}
        for item in items:
            if not item.proveedor_rut:
                continue
            bucket = by_proveedor.setdefault(
                item.proveedor_rut, {"nombre": item.proveedor_nombre, "monto": 0.0}
            )
            cantidad = item.cantidad_adjudicada if item.cantidad_adjudicada is not None else item.cantidad
            if item.monto_unitario is not None and cantidad is not None:
                bucket["monto"] += item.monto_unitario * cantidad

        upserted = 0
        for rut, data in by_proveedor.items():
            proveedor_id = self._resolve_proveedor(connection, rut, data["nombre"])
            monto_adjudicado = data["monto"] or None
            ratio = (
                round(monto_adjudicado / monto_estimado, 4)
                if monto_adjudicado is not None and monto_estimado
                else None
            )
            connection.execute(
                text(
                    "INSERT INTO core.adjudicacion "
                    "(licitacion_id, proveedor_id, organismo_id, monto_adjudicado, monto_estimado, "
                    "ratio_adjudicacion, cantidad_ofertas, fecha_adjudicacion, natural_key) "
                    "VALUES (:licitacion_id, :proveedor_id, :organismo_id, :monto_adjudicado, "
                    ":monto_estimado, :ratio_adjudicacion, :cantidad_ofertas, :fecha_adjudicacion, "
                    ":natural_key) "
                    "ON CONFLICT (natural_key) DO UPDATE SET "
                    "proveedor_id = :proveedor_id, organismo_id = :organismo_id, "
                    "monto_adjudicado = :monto_adjudicado, monto_estimado = :monto_estimado, "
                    "ratio_adjudicacion = :ratio_adjudicacion, cantidad_ofertas = :cantidad_ofertas, "
                    "fecha_adjudicacion = :fecha_adjudicacion, updated_at = now()"
                ),
                {
                    "licitacion_id": licitacion_id,
                    "proveedor_id": proveedor_id,
                    "organismo_id": organismo_id,
                    "monto_adjudicado": monto_adjudicado,
                    "monto_estimado": monto_estimado,
                    "ratio_adjudicacion": ratio,
                    "cantidad_ofertas": numero_oferentes,
                    "fecha_adjudicacion": fecha_adjudicacion,
                    "natural_key": natural_key("adjudicacion", f"{licitacion_codigo}:{rut}"),
                },
            )
            upserted += 1
        return upserted

    def _resolve_proveedor(
        self, connection: Connection, rut: str | None, razon_social: str | None
    ) -> int | None:
        if not rut:
            return None

        row = connection.execute(
            text("SELECT id FROM core.proveedor WHERE rut = :rut"), {"rut": rut}
        ).first()
        if row is not None:
            return int(row[0])

        inserted = connection.execute(
            text(
                "INSERT INTO core.proveedor (rut, razon_social, natural_key) "
                "VALUES (:rut, :razon_social, :natural_key) RETURNING id"
            ),
            {"rut": rut, "razon_social": razon_social, "natural_key": natural_key("proveedor", rut)},
        ).first()
        return int(inserted[0])

    def _resolve_organismo(
        self, connection: Connection, codigo: str | None, nombre: str | None
    ) -> int | None:
        if not codigo:
            return None

        row = connection.execute(
            text("SELECT id FROM core.organismo WHERE codigo = :codigo"), {"codigo": codigo}
        ).first()
        if row is not None:
            return int(row[0])

        inserted = connection.execute(
            text(
                "INSERT INTO core.organismo (codigo, nombre, natural_key) "
                "VALUES (:codigo, :nombre, :natural_key) RETURNING id"
            ),
            {"codigo": codigo, "nombre": nombre, "natural_key": natural_key("organismo", codigo)},
        ).first()
        return int(inserted[0])
