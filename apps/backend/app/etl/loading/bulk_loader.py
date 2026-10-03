from __future__ import annotations

import csv
import io
import logging
from typing import Any, Callable

from sqlalchemy import text

from app.etl.loading.dedup import classify_batch
from app.etl.loading.mapping import has_table, project_columns, table_for
from app.etl.models import IngestionRunContext, LoadResult, TransformedRecord

logger = logging.getLogger(__name__)


class BulkCopyLoader:
    """High-volume loader using PostgreSQL ``COPY`` semantics.

    Transformed records are grouped by target table and appended into a temp
    SQLAlchemy-agnostic flow. For real ``COPY`` this class is meant to be used
    with psycopg's ``copy_expert`` via the provided ``copy_writer``. A default
    in-memory writer is provided for tests/validation that writes CSV rows.
    """

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        copy_writer: Callable[[Any, str, list[str], list[list[Any]]], int]
        | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._copy_writer = copy_writer or _default_copy_writer

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
            by_table: dict[str, list[TransformedRecord]] = {}
            for record in records:
                if has_table(record.entity):
                    by_table.setdefault(record.entity, []).append(record)

            for entity, group in by_table.items():
                mapping = table_for(entity)
                columns, rows = self._rows_for(mapping, group)
                written = self._copy_writer(connection, mapping.table, columns, rows)
                result.inserted += written

        except Exception:
            logger.exception("Bulk COPY load failed for run=%s", run.ingestion_run_id)
            result.failed += len(records)
            raise
        finally:
            try:
                connection.close()
            except Exception:
                logger.debug("Error closing bulk connection", exc_info=True)

        return result

    def _rows_for(self, mapping, records) -> tuple[list[str], list[list[Any]]]:
        column_names: list[str] = []
        column_order: list[str] = []
        for field, column in mapping.columns.items():
            if column not in column_order:
                column_order.append(column)
        column_order.append(mapping.natural_key_column)
        column_order.append(mapping.payload_hash_column)
        if "source_id" not in column_order:
            column_order.append("source_id")
        if "ingestion_run_id" not in column_order:
            column_order.append("ingestion_run_id")

        column_names = column_order
        rows: list[list[Any]] = []
        for record in records:
            columns = project_columns(mapping, record.payload)
            columns[mapping.natural_key_column] = record.natural_key
            columns[mapping.payload_hash_column] = record.payload_hash
            columns["source_id"] = record.source_id
            columns["ingestion_run_id"] = (
                record.ingestion_run_id if hasattr(record, "ingestion_run_id") else None
            )
            rows.append([columns.get(name) for name in column_order])
        return column_names, rows


def _default_copy_writer(connection, table: str, columns: list[str], rows) -> int:
    """Write rows as CSV (compatible with ``COPY ... FROM STDIN``).

    This is a test-friendly implementation. For production, inject a writer
    using psycopg ``copy_expert`` targeting ``table``.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)
    return len(rows)
