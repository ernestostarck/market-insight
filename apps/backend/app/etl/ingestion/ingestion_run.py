from datetime import datetime, timezone
from uuid import uuid4

from app.etl.models import IngestionRunContext


def new_ingestion_run(
    *,
    source: str,
    resource: str,
    pipeline_version: str,
    params: dict[str, str] | None = None,
) -> IngestionRunContext:
    run_id = f"ETL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8]}"
    return IngestionRunContext(
        ingestion_run_id=run_id,
        source=source,
        resource=resource,
        pipeline_version=pipeline_version,
        started_at=datetime.now(timezone.utc),
        params=params or {},
    )
