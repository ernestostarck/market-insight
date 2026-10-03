from datetime import datetime, timezone

import pytest
from app.etl.extraction.base import ExtractionWindow
from app.etl.extraction.checkpoints import (
    ExtractionCheckpoint,
    InMemoryCheckpointStore,
)
from app.etl.extraction.chilecompra import ChileCompraAPIDataSource
from app.etl.ingestion.ingestion_run import new_ingestion_run


class FakeLicitacionesClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def por_fecha(self, fecha: str):
        self.calls.append(fecha)
        if fecha == "06082026":
            return {
                "Listado": [
                    {"CodigoExterno": "1000-1-LR26", "Estado": "ADJUDICADA"},
                    {"CodigoExterno": "1000-2-LR26", "Estado": "PUBLICADA"},
                ]
            }
        if fecha == "07082026":
            return {"Listado": []}
        return {"Listado": []}


class FakeSDKClient:
    def __init__(self) -> None:
        self.licitaciones = FakeLicitacionesClient()


@pytest.mark.asyncio
async def test_chilecompra_source_extracts_by_window_and_updates_checkpoint() -> None:
    checkpoint_store = InMemoryCheckpointStore()
    source = ChileCompraAPIDataSource(
        client=FakeSDKClient(),
        checkpoint_store=checkpoint_store,
    )
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.2.0",
    )

    records = await source.extract(
        run=run,
        window=ExtractionWindow(
            start_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
            end_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        ),
    )

    assert len(records) == 2
    assert records[0].source_id == "1000-1-LR26"
    assert records[0].metadata["snapshot_date"] == "2026-08-06"

    checkpoint = checkpoint_store.get(source="chilecompra_api", resource="licitaciones")
    assert checkpoint is not None
    assert checkpoint.marker == "2026-08-06"


@pytest.mark.asyncio
async def test_chilecompra_source_uses_checkpoint_when_window_missing() -> None:
    checkpoint_store = InMemoryCheckpointStore()
    checkpoint_store.set(
        ExtractionCheckpoint(
            source="chilecompra_api",
            resource="licitaciones",
            marker="2026-08-06",
            updated_at=datetime.now(timezone.utc),
        )
    )
    source = ChileCompraAPIDataSource(
        client=FakeSDKClient(),
        checkpoint_store=checkpoint_store,
    )
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.2.0",
    )

    records = await source.extract(run=run)

    assert len(records) == 0


@pytest.mark.asyncio
async def test_chilecompra_source_rejects_invalid_checkpoint_marker() -> None:
    checkpoint_store = InMemoryCheckpointStore()
    checkpoint_store.set(
        ExtractionCheckpoint(
            source="chilecompra_api",
            resource="licitaciones",
            marker="invalid-date-marker",
            updated_at=datetime.now(timezone.utc),
        )
    )
    source = ChileCompraAPIDataSource(
        client=FakeSDKClient(),
        checkpoint_store=checkpoint_store,
    )
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.2.0",
    )

    with pytest.raises(ValueError, match="invalid checkpoint marker"):
        await source.extract(run=run)


@pytest.mark.asyncio
async def test_chilecompra_source_rejects_inverted_window() -> None:
    source = ChileCompraAPIDataSource(client=FakeSDKClient())
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.2.0",
    )

    with pytest.raises(ValueError, match="window end_at"):
        await source.extract(
            run=run,
            window=ExtractionWindow(
                start_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
                end_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
            ),
        )
