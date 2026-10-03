from __future__ import annotations

import logging
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.etl.loading.dedup import ExistingRecordLookup, classify_batch
from app.etl.loading.mapping import (
    has_table,
    project_columns,
    table_for,
)
from app.etl.models import IngestionRunContext, LoadResult, TransformedRecord

logger = logging.getLogger(__name__)


class PostgresRecordLoader:
    """Load transformed records into the procurement.* analytical tables.

    Implementation uses SQLAlchemy Core and performs an upsert keyed on the
    natural key with deduplication via ``payload_hash``. Records that already
    exist with an identical hash are counted as ``unchanged`` and skipped.
    """

    def __init__(
        self,
        connection_factory,
        *,
        batch_size: int = 500,
    ) -> None:
        self._connection_factory = connection_factory
        self._batch_size = batch_size

    def load(
        self,
        run: IngestionRunContext,
        records: list[TransformedRecord],
    ) -> LoadResult:
        result = LoadResult()
        if not records:
            return result

        connection = self._connection_factory()
        try:
            buckets = classify_batch(records, self._existing_hash_lookup(connection))

            for record in buckets["insert"]:
                self._upsert(connection, record, run)
                result.inserted += 1

            for record in buckets["update"]:
                self._upsert(connection, record, run)
                result.updated += 1

            result.unchanged = len(buckets["unchanged"])
        except Exception:
            logger.exception(
                "Postgres ETL load failed for run=%s", run.ingestion_run_id
            )
            result.failed += len(records)
            raise
        finally:
            self._close(connection)

        return result

    def _existing_hash_lookup(self, connection: Connection) -> ExistingRecordLookup:
        def lookup(entity: str, natural_key: str) -> str | None:
            if not has_table(entity):
                return None
            mapping = table_for(entity)
            qualified = f"{mapping.schema}.{mapping.table}"
            stmt = text(
                f"SELECT {mapping.payload_hash_column} FROM {qualified} "
                f"WHERE {mapping.natural_key_column} = :natural_key"
            )
            row = connection.execute(stmt, {"natural_key": natural_key}).first()
            if row is None:
                return None
            return str(row[0])

        return lookup

    def _upsert(
        self,
        connection: Connection,
        record: TransformedRecord,
        run: IngestionRunContext,
    ) -> None:
        if not has_table(record.entity):
            logger.warning(
                "Skipping record with no target table: entity=%s key=%s",
                record.entity,
                record.natural_key,
            )
            return None

        mapping = table_for(record.entity)
        qualified = f"{mapping.schema}.{mapping.table}"
        columns = project_columns(mapping, record.payload)
        columns[mapping.natural_key_column] = record.natural_key
        columns[mapping.payload_hash_column] = record.payload_hash
        columns["source_id"] = record.source_id
        columns["ingestion_run_id"] = run.ingestion_run_id

        column_names = list(columns.keys())
        placeholders = ", ".join(f":{name}" for name in column_names)
        col_decl = ", ".join(column_names)

        update_assignments = [
            f"{name} = excluded.{name}"
            for name in column_names
            if name not in (mapping.natural_key_column,)
        ]
        conflict_target = f"({mapping.natural_key_column})"
        upsert_sql = (
            f"INSERT INTO {qualified} ({col_decl}) VALUES ({placeholders}) "
            f"ON CONFLICT {conflict_target} DO UPDATE SET "
            + ", ".join(update_assignments)
        )
        connection.execute(text(upsert_sql), columns)
        return None

    def _close(self, connection: Connection) -> None:
        try:
            connection.close()
        except Exception:
            logger.debug("Error closing ETL connection", exc_info=True)


class EngineConnectionFactory:
    """Simple factory returning a connection from a SQLAlchemy Engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __call__(self) -> Connection:
        return self._engine.connect()
