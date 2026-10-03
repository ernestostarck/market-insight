"""Checkpoint persistence for incremental ETL loads.

A checkpoint captures *how far a stream has progressed* so that the next run
can resume exactly where the previous one finished. We offer two backends:

* :class:`InMemoryCheckpointStore` — useful for tests, validation and single
  process local runs (loses state on restart).
* :class:`SqlAlchemyCheckpointStore` — durable, backed by the
  ``etl.etl_incremental_checkpoints`` table; safe to share across workers.

Both implement the same :class:`CheckpointStore` base class so the planner and
engine remain storage-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.etl.incremental.models import IncrementalCheckpoint


# --------------------------------------------------------------------------- #
# Domain record + storage contract
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class IncrementalCheckpointRecord:
    """A lightweight domain copy of a checkpoint row."""

    source: str
    resource: str
    marker: str | None
    updated_at: datetime
    last_status: str = "unknown"


class CheckpointStore:
    """Contract implemented by every checkpoint backend."""

    def get(self, *, source: str, resource: str) -> IncrementalCheckpoint | None:
        raise NotImplementedError

    def set(self, checkpoint: IncrementalCheckpoint) -> None:
        raise NotImplementedError

    def reset(self, *, source: str, resource: str) -> None:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# SQLAlchemy model (persistent backend)
# --------------------------------------------------------------------------- #
class IncrementalCheckpointModel(Base):
    __tablename__ = "etl_incremental_checkpoints"
    __table_args__ = {"schema": "etl"}

    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource: Mapped[str] = mapped_column(String(64), primary_key=True)
    marker: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_status: Mapped[str] = mapped_column(
        String(32), default="unknown", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SqlAlchemyCheckpointStore(CheckpointStore):
    """Durable checkpoint store backed by PostgreSQL.

    Uses a connection factory so it can run both inside FastAPI request/worker
    contexts (via ``SessionLocal``) and from standalone scripts.
    """

    def __init__(self, connection_factory) -> None:
        self._connection_factory = connection_factory

    def get(self, *, source: str, resource: str) -> IncrementalCheckpoint | None:
        connection = self._connection_factory()
        try:
            stmt = text(
                "SELECT source, resource, marker, last_status, updated_at "
                "FROM etl.etl_incremental_checkpoints "
                "WHERE source = :source AND resource = :resource"
            )
            row = connection.execute(
                stmt, {"source": source, "resource": resource}
            ).first()
        finally:
            self._close(connection)

        if row is None:
            return None
        return IncrementalCheckpoint(
            source=row[0],
            resource=row[1],
            marker=row[2],
            updated_at=row[4],
            last_status=str(row[3]),
        )

    def set(self, checkpoint: IncrementalCheckpoint) -> None:
        connection = self._connection_factory()
        try:
            stmt = text(
                "INSERT INTO etl.etl_incremental_checkpoints "
                "(source, resource, marker, last_status, updated_at) "
                "VALUES (:source, :resource, :marker, :last_status, :updated_at) "
                "ON CONFLICT (source, resource) DO UPDATE SET "
                "marker = excluded.marker, "
                "last_status = excluded.last_status, "
                "updated_at = excluded.updated_at"
            )
            connection.execute(
                stmt,
                {
                    "source": checkpoint.source,
                    "resource": checkpoint.resource,
                    "marker": checkpoint.marker,
                    "last_status": checkpoint.last_status,
                    "updated_at": checkpoint.updated_at,
                },
            )
            connection.commit()
        finally:
            self._close(connection)

    def reset(self, *, source: str, resource: str) -> None:
        connection = self._connection_factory()
        try:
            stmt = text(
                "DELETE FROM etl.etl_incremental_checkpoints "
                "WHERE source = :source AND resource = :resource"
            )
            connection.execute(stmt, {"source": source, "resource": resource})
            connection.commit()
        finally:
            self._close(connection)

    def _close(self, connection) -> None:
        try:
            connection.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# In-memory backend
# --------------------------------------------------------------------------- #
class InMemoryCheckpointStore(CheckpointStore):
    """Transient checkpoint store keyed by (source, resource).

    Useful for tests and single-process validation runs. State is lost when
    the process exits.
    """

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], IncrementalCheckpoint] = {}

    def get(self, *, source: str, resource: str) -> IncrementalCheckpoint | None:
        return self._items.get((source, resource))

    def set(self, checkpoint: IncrementalCheckpoint) -> None:
        self._items[(checkpoint.source, checkpoint.resource)] = checkpoint

    def reset(self, *, source: str, resource: str) -> None:
        self._items.pop((source, resource), None)

    def __len__(self) -> int:
        return len(self._items)


# --------------------------------------------------------------------------- #
# Facade / helper
# --------------------------------------------------------------------------- #
class IncrementalCheckpointer:
    """High level API wrapping a :class:`CheckpointStore`.

    Adds convenience methods (``advance``, ``mark``) and validation on top of
    the raw store, keeping callers decoupled from the concrete backend.
    """

    def __init__(self, store: CheckpointStore) -> None:
        self._store = store

    @property
    def store(self) -> CheckpointStore:
        return self._store

    def get(self, *, source: str, resource: str) -> IncrementalCheckpoint | None:
        return self._store.get(source=source, resource=resource)

    def set(self, checkpoint: IncrementalCheckpoint) -> None:
        self._store.set(checkpoint)

    def reset(self, *, source: str, resource: str) -> None:
        self._store.reset(source=source, resource=resource)

    def advance(
        self,
        *,
        source: str,
        resource: str,
        marker: str | None,
        status: str = "succeeded",
        updated_at: datetime | None = None,
    ) -> IncrementalCheckpoint:
        """Persist ``marker`` as the new watermark for the stream."""
        checkpoint = IncrementalCheckpoint(
            source=source,
            resource=resource,
            marker=marker,
            last_status=status,
            updated_at=updated_at or _utcnow(),
        )
        self._store.set(checkpoint)
        return checkpoint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
