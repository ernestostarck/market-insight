"""Unit tests for MLOps pipeline, regression validation, promotion policy and tracking (Fase 6.23)."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from app.nlp.classifier_training import EvaluationResult, TrainingExample
from app.nlp.mlops.pipeline import (
    PromotionPolicy,
    RegressionValidator,
    ReproducibleTrainingPipeline,
)
from app.nlp.mlops.tracking import MLflowTracker


def _create_eval_result(f1_macro: float, acc: float, class_f1: dict[str, float]) -> EvaluationResult:
    per_class = {label: {"f1-score": score, "precision": score, "recall": score, "support": 10} for label, score in class_f1.items()}
    return EvaluationResult(
        accuracy=acc,
        precision_macro=f1_macro,
        recall_macro=f1_macro,
        f1_macro=f1_macro,
        per_class=per_class,
        confusion_matrix=[[10, 0], [0, 10]],
        labels=tuple(sorted(class_f1.keys())),
    )


def test_regression_validator_passes_when_better_or_equal() -> None:
    prod_eval = _create_eval_result(0.85, 0.85, {"SALUD": 0.88, "TECNOLOGIA": 0.82})
    cand_eval = _create_eval_result(0.87, 0.87, {"SALUD": 0.89, "TECNOLOGIA": 0.85})

    validator = RegressionValidator(max_allowed_f1_drop=0.05)
    check = validator.validate(cand_eval, prod_eval)

    assert not check.has_regressions
    assert len(check.violations) == 0


def test_regression_validator_fails_on_macro_regression() -> None:
    prod_eval = _create_eval_result(0.85, 0.85, {"SALUD": 0.88, "TECNOLOGIA": 0.82})
    cand_eval = _create_eval_result(0.78, 0.80, {"SALUD": 0.80, "TECNOLOGIA": 0.76})

    validator = RegressionValidator(max_allowed_f1_drop=0.05)
    check = validator.validate(cand_eval, prod_eval)

    assert check.has_regressions
    assert any("Macro F1 cayó" in v for v in check.violations)


def test_regression_validator_fails_on_per_class_regression() -> None:
    prod_eval = _create_eval_result(0.85, 0.85, {"SALUD": 0.90, "TECNOLOGIA": 0.80})
    # Overall macro is only 0.02 lower, but TECNOLOGIA dropped by 0.08
    cand_eval = _create_eval_result(0.83, 0.84, {"SALUD": 0.94, "TECNOLOGIA": 0.72})

    validator = RegressionValidator(max_allowed_f1_drop=0.05)
    check = validator.validate(cand_eval, prod_eval)

    assert check.has_regressions
    assert any("TECNOLOGIA" in v for v in check.violations)


def test_promotion_policy_evaluation() -> None:
    policy = PromotionPolicy(min_f1_macro=0.75, min_accuracy=0.70, max_regression_margin=0.05)

    prod_eval = _create_eval_result(0.80, 0.80, {"SALUD": 0.80})

    # Case 1: Meets all criteria
    good_cand = _create_eval_result(0.82, 0.82, {"SALUD": 0.82})
    eligible, violations = policy.evaluate_promotion(good_cand, prod_eval)
    assert eligible
    assert len(violations) == 0

    # Case 2: Below minimum F1 macro
    low_cand = _create_eval_result(0.72, 0.75, {"SALUD": 0.72})
    eligible, violations = policy.evaluate_promotion(low_cand, prod_eval)
    assert not eligible
    assert any("F1 macro" in v for v in violations)


def test_reproducible_training_pipeline() -> None:
    train_data = [
        TrainingExample(1, "compra de insumos medicos jeringas y vacunas de hospital salud", "SALUD", "train"),
        TrainingExample(2, "licitacion de paracetamol y gasas para clinica y salud", "SALUD", "train"),
        TrainingExample(3, "desarrollo de software sistemas y servidores de tecnologia", "TECNOLOGIA", "train"),
        TrainingExample(4, "licencias de base de datos postgres y computadores tecnologia", "TECNOLOGIA", "train"),
    ] * 5

    val_data = [
        TrainingExample(5, "suministro de vacunas e insumos medicos de salud", "SALUD", "val"),
        TrainingExample(6, "soporte y mantenimiento de software y computadores tecnologia", "TECNOLOGIA", "val"),
    ] * 3

    test_data = [
        TrainingExample(7, "adquisicion de vacunas medicamentos para hospital de salud", "SALUD", "test"),
        TrainingExample(8, "equipamiento de tecnologia redes servidores y computadores", "TECNOLOGIA", "test"),
    ] * 3

    # Fake embedding service
    mock_embed = MagicMock()
    mock_embed.encode.side_effect = lambda texts: np.random.RandomState(42).randn(len(texts), 16)

    pipeline = ReproducibleTrainingPipeline(random_state=42)
    summary = pipeline.run(
        train_examples=train_data,
        val_examples=val_data,
        test_examples=test_data,
        embedding_service=mock_embed,
        dataset_version_id="dataset-v1-uuid",
    )

    assert summary.winner_name in ("tfidf_logreg", "embeddings_logreg")
    assert summary.test_metrics.accuracy > 0.5
    assert summary.hyperparameters["random_state"] == 42
    assert summary.dataset_version_id == "dataset-v1-uuid"
    assert "SALUD" in summary.labels
    assert "TECNOLOGIA" in summary.labels


def test_mlflow_tracker_offline_fallback() -> None:
    # Tracker with no remote URI should operate safely in-memory
    tracker = MLflowTracker(tracking_uri=None)
    assert not tracker.is_connected

    run_id = tracker.start_run(experiment_name="nlp-classification", run_name="exp-1")
    assert run_id.startswith("local-run-")

    tracker.log_param("max_iter", 1000)
    tracker.log_metric("f1_macro", 0.8842)
    tracker.log_artifact("model.joblib", "models")
    tracker.end_run(status="FINISHED")

    data = tracker.get_logged_data()
    assert data["experiment"] == "nlp-classification"
    assert data["params"]["max_iter"] == 1000
    assert data["metrics"]["f1_macro"] == 0.8842
    assert len(data["artifacts"]) == 1
    assert data["status"] == "FINISHED"
