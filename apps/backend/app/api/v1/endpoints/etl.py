from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.etl.orchestration.jobs import sync_all_resources, sync_resource
from app.schemas.etl import (
    ETLJobResponse,
    ETLJobStatusResponse,
    SyncAllResourcesRequest,
    SyncResourceRequest,
)

router = APIRouter()


@router.post(
    "/sync-resource",
    response_model=ETLJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger ETL for a Single Resource",
    tags=["ETL"],
)
def trigger_sync_resource(
    request: SyncResourceRequest,
):
    """
    Enqueue a background job to synchronize a single resource from a data source.

    This endpoint is asynchronous. It returns a task ID that can be used to
    monitor the job's progress via the `/jobs/{task_id}` endpoint.
    """
    task = sync_resource.delay(
        resource=str(request.resource),
        source=request.source,
        force_backfill=request.force_backfill,
        history_start=str(request.history_start) if request.history_start else None,
        end_at=str(request.end_at) if request.end_at else None,
    )
    return {"task_id": task.id}


@router.post(
    "/sync-all-resources",
    response_model=ETLJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger ETL for Multiple Resources",
    tags=["ETL"],
)
def trigger_sync_all_resources(
    request: SyncAllResourcesRequest,
):
    """
    Enqueue a background job to synchronize multiple resources from a data source.

    This endpoint is asynchronous. It returns a task ID that can be used to
    monitor the job's progress via the `/jobs/{task_id}` endpoint.
    """
    task = sync_all_resources.delay(
        resources=[str(r) for r in request.resources] if request.resources else None,
        source=request.source,
    )
    return {"task_id": task.id}


@router.get(
    "/jobs/{task_id}",
    response_model=ETLJobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ETL Job Status",
    tags=["ETL"],
)
def get_job_status(task_id: str):
    """
    Retrieve the status and result of a background ETL job.
    """
    task_result = AsyncResult(task_id)
    result = task_result.result if task_result.ready() else None
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"task_id": task_id, "status": task_result.status, "result": result},
    )
