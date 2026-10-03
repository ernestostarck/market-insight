"""MLOps reproducible training, evaluation, regression validation and promotion policy (Fase 6.23)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sklearn.pipeline import Pipeline

from app.nlp.classifier_training import (
    EvaluationResult,
    TrainingExample,
    evaluate,
    train_and_select,
)


@dataclass(frozen=True, slots=True)
class RegressionCheckResult:
    has_regressions: bool
    violations: tuple[str, ...]


class RegressionValidator:
    """Validates that a candidate model does not regress significantly against the production model."""

    def __init__(self, max_allowed_f1_drop: float = 0.05) -> None:
        self.max_allowed_f1_drop = max_allowed_f1_drop

    def validate(
        self,
        candidate_eval: EvaluationResult,
        production_eval: EvaluationResult,
    ) -> RegressionCheckResult:
        violations: list[str] = []

        # 1. Macro F1 regression check
        if candidate_eval.f1_macro < (production_eval.f1_macro - self.max_allowed_f1_drop):
            violations.append(
                f"Macro F1 cayó de {production_eval.f1_macro:.4f} a {candidate_eval.f1_macro:.4f} "
                f"(tolerancia máxima: {self.max_allowed_f1_drop})"
            )

        # 2. Per-class F1 regression check
        for label, prod_metrics in production_eval.per_class.items():
            if label not in candidate_eval.per_class:
                violations.append(f"Clase '{label}' no evaluada en el modelo candidato")
                continue

            prod_f1 = prod_metrics.get("f1-score", 0.0)
            cand_f1 = candidate_eval.per_class[label].get("f1-score", 0.0)

            if cand_f1 < (prod_f1 - self.max_allowed_f1_drop):
                violations.append(
                    f"F1 de la clase '{label}' cayó de {prod_f1:.4f} a {cand_f1:.4f} "
                    f"(diferencia: {prod_f1 - cand_f1:.4f} > {self.max_allowed_f1_drop})"
                )

        return RegressionCheckResult(
            has_regressions=len(violations) > 0,
            violations=tuple(violations),
        )


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    """Defines strict gating rules required to promote a model to staging or production."""

    min_f1_macro: float = 0.70
    min_accuracy: float = 0.65
    max_regression_margin: float = 0.05

    def evaluate_promotion(
        self,
        candidate_eval: EvaluationResult,
        production_eval: EvaluationResult | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if candidate_eval.f1_macro < self.min_f1_macro:
            reasons.append(
                f"F1 macro ({candidate_eval.f1_macro:.4f}) no alcanza el umbral mínimo de {self.min_f1_macro:.4f}"
            )

        if candidate_eval.accuracy < self.min_accuracy:
            reasons.append(
                f"Accuracy ({candidate_eval.accuracy:.4f}) no alcanza el umbral mínimo de {self.min_accuracy:.4f}"
            )

        if production_eval is not None:
            validator = RegressionValidator(self.max_regression_margin)
            reg_check = validator.validate(candidate_eval, production_eval)
            if reg_check.has_regressions:
                reasons.extend(reg_check.violations)

        is_eligible = len(reasons) == 0
        return is_eligible, reasons


@dataclass(frozen=True, slots=True)
class TrainingRunSummary:
    winner_name: str
    winner_pipeline: Pipeline
    train_metrics: EvaluationResult
    validation_metrics: EvaluationResult
    test_metrics: EvaluationResult
    hyperparameters: dict[str, Any]
    dataset_version_id: str | None
    labels: tuple[str, ...]


class ReproducibleTrainingPipeline:
    """Coordinates deterministic training, multi-baseline selection, and held-out evaluation."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state

    def run(
        self,
        train_examples: list[TrainingExample],
        val_examples: list[TrainingExample],
        test_examples: list[TrainingExample],
        embedding_service: Any,
        dataset_version_id: str | None = None,
    ) -> TrainingRunSummary:
        winner_name, winner_pipeline, train_eval, val_eval = train_and_select(
            train_examples,
            val_examples,
            embedding_service,
            random_state=self.random_state,
        )

        labels = tuple(sorted(
            {ex.label for ex in train_examples}
            | {ex.label for ex in val_examples}
            | {ex.label for ex in test_examples}
        ))

        # Held-out test split evaluation
        test_eval = evaluate(winner_pipeline, test_examples, labels=labels)

        hyperparameters = {
            "random_state": self.random_state,
            "winner_model": winner_name,
            "train_samples": len(train_examples),
            "val_samples": len(val_examples),
            "test_samples": len(test_examples),
            "dataset_version_id": dataset_version_id,
        }

        return TrainingRunSummary(
            winner_name=winner_name,
            winner_pipeline=winner_pipeline,
            train_metrics=train_eval,
            validation_metrics=val_eval,
            test_metrics=test_eval,
            hyperparameters=hyperparameters,
            dataset_version_id=dataset_version_id,
            labels=labels,
        )
