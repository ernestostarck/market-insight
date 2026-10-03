"""Incremental (delta) ETL loads.

This package implements fase 3.9: it lets streams resume from persisted
checkpoints, plan backfill/incremental windows, and execute them through the
ETL pipeline while advancing the watermark only on success.

Public API
----------
* :class:`IncrementalETL` — high level engine (also re-exported for
  compatibility with legacy ``worker/tasks.py``).
* :class:`IncrementalPlanner` — decides backfill vs incremental windows.
* :class:`IncrementalCheckpointer` / :class:`InMemoryCheckpointStore` /
  :class:`SqlAlchemyCheckpointStore` — checkpoint persistence backends.
* Domain models: :class:`IncrementalWindow`, :class:`IncrementalPlan`,
  :class:`IncrementalRun`, :class:`IncrementalCheckpoint`.
"""

from __future__ import annotations

from app.etl.incremental.checkpointer import (
    CheckpointStore,
    IncrementalCheckpointer,
    IncrementalCheckpointModel,
    IncrementalCheckpointRecord,
    InMemoryCheckpointStore,
    SqlAlchemyCheckpointStore,
)
from app.etl.incremental.engine import IncrementalETL
from app.etl.incremental.models import (
    IncrementalCheckpoint,
    IncrementalLoadTrigger,
    IncrementalPlan,
    IncrementalRun,
    IncrementalRunStatus,
    IncrementalWindow,
)
from app.etl.incremental.window import IncrementalPlanner

__all__ = [
    "IncrementalETL",
    "IncrementalPlanner",
    "IncrementalCheckpointer",
    "InMemoryCheckpointStore",
    "SqlAlchemyCheckpointStore",
    "CheckpointStore",
    "IncrementalCheckpoint",
    "IncrementalCheckpointRecord",
    "IncrementalCheckpointModel",
    "IncrementalWindow",
    "IncrementalPlan",
    "IncrementalRun",
    "IncrementalRunStatus",
    "IncrementalLoadTrigger",
]
