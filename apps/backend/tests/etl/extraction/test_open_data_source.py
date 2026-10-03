import json

import pytest
from app.etl.extraction.checkpoints import InMemoryCheckpointStore
from app.etl.extraction.open_data import OpenDataDataSource
from app.etl.ingestion.ingestion_run import new_ingestion_run


@pytest.mark.asyncio
async def test_open_data_source_bulk_batches_with_checkpoint(tmp_path) -> None:
    dataset = tmp_path / "licitaciones.ndjson"
    rows = [
        {"codigo": "A-1", "estado": "ADJUDICADA"},
        {"codigo": "A-2", "estado": "PUBLICADA"},
        {"codigo": "A-3", "estado": "DESIERTA"},
    ]
    dataset.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    store = InMemoryCheckpointStore()
    source = OpenDataDataSource(
        dataset_path=dataset,
        resource="licitaciones_historicas",
        source_id_field="codigo",
        checkpoint_store=store,
    )
    run1 = new_ingestion_run(
        source="open_data",
        resource="licitaciones_historicas",
        pipeline_version="3.2.0",
        params={"batch_size": "2"},
    )
    first_batch = await source.extract(run=run1)

    assert [item.source_id for item in first_batch] == ["A-1", "A-2"]
    checkpoint = store.get(source="open_data", resource="licitaciones_historicas")
    assert checkpoint is not None
    assert checkpoint.marker == "2"

    run2 = new_ingestion_run(
        source="open_data",
        resource="licitaciones_historicas",
        pipeline_version="3.2.0",
        params={"batch_size": "2"},
    )
    second_batch = await source.extract(run=run2)

    assert [item.source_id for item in second_batch] == ["A-3"]


@pytest.mark.asyncio
async def test_open_data_source_invalid_batch_size(tmp_path) -> None:
    dataset = tmp_path / "licitaciones.ndjson"
    dataset.write_text(json.dumps({"codigo": "A-1"}) + "\n", encoding="utf-8")

    source = OpenDataDataSource(
        dataset_path=dataset,
        resource="licitaciones_historicas",
        source_id_field="codigo",
    )
    run = new_ingestion_run(
        source="open_data",
        resource="licitaciones_historicas",
        pipeline_version="3.2.0",
        params={"batch_size": "0"},
    )

    with pytest.raises(ValueError, match="batch_size"):
        await source.extract(run=run)


@pytest.mark.asyncio
async def test_open_data_source_fallback_source_id(tmp_path) -> None:
    dataset = tmp_path / "licitaciones.ndjson"
    dataset.write_text(json.dumps({"estado": "ADJUDICADA"}) + "\n", encoding="utf-8")

    source = OpenDataDataSource(
        dataset_path=dataset,
        resource="licitaciones_historicas",
        source_id_field="codigo",
    )
    run = new_ingestion_run(
        source="open_data",
        resource="licitaciones_historicas",
        pipeline_version="3.2.0",
    )

    records = await source.extract(run=run)

    assert len(records) == 1
    assert records[0].source_id == "line-0"
