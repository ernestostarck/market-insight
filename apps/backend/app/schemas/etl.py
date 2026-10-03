from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.etl.orchestration.jobs import DEFAULT_RESOURCES


class SupportedResource(str, Enum):
    """ETL-supported resources that can be synchronized."""

    LICITACIONES = "licitaciones"
    ORDENES_DE_COMPRA = "ordenes_compra"
    EMPRESAS = "empresas"
    CONTRATOS = "contratos"
    CONVENIOS_MARCO = "convenios_marco"
    ADJUDICACIONES = "adjudicaciones"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls}

    def __str__(self) -> str:
        return self.value


class SyncResourceRequest(BaseModel):
    """Request model for triggering a single resource sync."""

    resource: SupportedResource = Field(
        ...,
        description="The resource to synchronize.",
        examples=["licitaciones"],
    )
    source: str = Field(
        "chilecompra_api",
        description="The data source to sync from.",
        examples=["chilecompra_api"],
    )
    force_backfill: bool = Field(
        False,
        description="If true, forces a full history backfill, ignoring existing checkpoints.",
    )
    history_start: date | None = Field(
        None,
        description="ISO 8601 date to start the sync from if no checkpoint exists.",
        examples=["2023-01-01"],
    )
    end_at: datetime | None = Field(
        None,
        description="ISO 8601 datetime to sync up to. Defaults to now.",
        examples=["2023-01-31T23:59:59"],
    )


class SyncAllResourcesRequest(BaseModel):
    """Request model for triggering a sync of multiple resources."""

    resources: list[SupportedResource] | None = Field(
        None,
        description=f"List of resources to sync. Defaults to all: {', '.join(DEFAULT_RESOURCES)}.",
    )
    source: str = Field(
        "chilecompra_api",
        description="The data source to sync from.",
        examples=["chilecompra_api"],
    )


class JobStatus(str, Enum):
    """Celery task states."""

    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class ETLJobResponse(BaseModel):
    """Response model for a triggered ETL job."""

    task_id: str = Field(..., description="The ID of the background task.", examples=["a-celery-task-id"])


class ETLJobStatusResponse(BaseModel):
    """Response model for the status of an ETL job."""

    task_id: str = Field(..., description="The ID of the background task.")
    status: JobStatus = Field(..., description="The current status of the task.")
    result: Any | None = Field(None, description="The result of the task if it has completed.")
