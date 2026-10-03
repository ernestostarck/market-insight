"""Classifier training CLI (Fase 6.14). Run as
``python -m app.nlp.classifier_training_cli train``.

Trains both baselines (app/nlp/classifier_training.py) on the active (or
given) Gold Dataset version, selects the winner by validation f1_macro,
evaluates it once on the held-out test split, persists the fitted
pipeline to MinIO, and registers a `knowledge.model_versions` row —
status "staging" (promotion to "production" is a business decision, not
something this pipeline decides on its own; see
app/nlp/contracts.py::validate_model_transition).
"""

from __future__ import annotations

import argparse
import sys
import uuid
from io import BytesIO

import joblib
from minio import Minio
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.infrastructure.storage.minio_storage import MinioObjectStorage
from app.ml.embeddings import EmbeddingService
from app.nlp.classifier_training import TrainingExample, evaluate, train_and_select
from app.nlp.classifier_training_db import register_model_version, set_artifact_uri
from app.nlp.gold_dataset_db import ensure_documents, fetch_training_rows

_MODEL_NAME_BY_CANDIDATE = {"tfidf_logreg": "tfidf-logreg", "embeddings_logreg": "embeddings-logreg"}


def _engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def _minio_storage() -> MinioObjectStorage:
    settings = get_settings()
    client = Minio(
        endpoint=settings.minio_endpoint, access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key, secure=False,
    )
    return MinioObjectStorage(client)


def _resolve_dataset_version_id(connection, given: str | None) -> uuid.UUID:
    if given:
        return uuid.UUID(given)
    row = connection.execute(
        text("SELECT id FROM knowledge.dataset_versions WHERE name = 'gold-dataset' ORDER BY created_at DESC LIMIT 1")
    ).first()
    if row is None:
        raise SystemExit("no dataset_versions row found — run `gold_dataset_cli sample/label/split/finalize` first")
    return row[0]


def cmd_train(args: argparse.Namespace) -> None:
    engine = _engine()
    connection = engine.connect()
    try:
        dataset_version_id = _resolve_dataset_version_id(connection, args.dataset_version)
        licitacion_ids = [
            row[0] for row in connection.execute(
                text(
                    "SELECT licitacion_id FROM knowledge.gold_labels "
                    "WHERE dataset_version_id = :dataset_version_id AND relevant IS NOT NULL"
                ),
                {"dataset_version_id": dataset_version_id},
            ).all()
        ]
        ensure_documents(connection, licitacion_ids)
        connection.commit()

        training_rows = fetch_training_rows(connection, dataset_version_id)
    finally:
        connection.close()

    examples = [
        TrainingExample(licitacion_id=row["licitacion_id"], text=row["text"], label=row["label"], split=row["split"])
        for row in training_rows
    ]
    train = [example for example in examples if example.split == "train"]
    validation = [example for example in examples if example.split == "validation"]
    test = [example for example in examples if example.split == "test"]
    if not train or not validation:
        raise SystemExit(
            f"dataset_version {dataset_version_id} needs data in both train and validation splits "
            f"(got train={len(train)}, validation={len(validation)}) — run `gold_dataset_cli split` first"
        )

    print(f"dataset_version={dataset_version_id} train={len(train)} validation={len(validation)} test={len(test)}")

    embedding_service = EmbeddingService()
    winner_candidate, winner_pipeline, train_eval, validation_eval = train_and_select(train, validation, embedding_service)

    labels = tuple(sorted({e.label for e in train} | {e.label for e in validation} | {e.label for e in test}))
    test_eval = evaluate(winner_pipeline, test, labels=labels) if test else None

    buffer = BytesIO()
    joblib.dump(winner_pipeline, buffer)

    storage = _minio_storage()
    bucket = get_settings().minio_bucket_ml_models
    storage.ensure_bucket(bucket)
    model_name = _MODEL_NAME_BY_CANDIDATE[winner_candidate]
    object_name = f"{model_name}/{args.version}.joblib"
    artifact_uri = storage.upload(bucket, object_name, buffer.getvalue(), "application/octet-stream")

    metrics = {"train": train_eval.to_dict(), "validation": validation_eval.to_dict()}
    if test_eval is not None:
        metrics["test"] = test_eval.to_dict()

    connection = engine.connect()
    try:
        model_version_id = register_model_version(
            connection, name=model_name, version=args.version, status="staging",
            parameters={"dataset_version_id": str(dataset_version_id), "labels": list(labels)},
            metrics=metrics,
        )
        set_artifact_uri(connection, model_version_id, artifact_uri)
        connection.commit()
    finally:
        connection.close()

    print(f"\nwinner={model_name} model_version_id={model_version_id}")
    print(f"artifact_uri={artifact_uri}")
    print(f"validation: accuracy={validation_eval.accuracy:.3f} f1_macro={validation_eval.f1_macro:.3f}")
    if test_eval is not None:
        print(f"test:       accuracy={test_eval.accuracy:.3f} f1_macro={test_eval.f1_macro:.3f}")
    print("\nvalidation per-class:")
    for label, values in validation_eval.per_class.items():
        print(f"  {label}: precision={values['precision']:.3f} recall={values['recall']:.3f} "
              f"f1={values['f1-score']:.3f} support={values['support']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Classifier training CLI (Fase 6.14)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="train, select, persist and register a classifier")
    train_parser.add_argument("--dataset-version", default=None, help="dataset_versions.id (UUID); default: latest gold-dataset")
    train_parser.add_argument("--version", default="v1", help="ModelVersion.version tag for the selected model")
    train_parser.set_defaults(func=cmd_train)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
