"""Supervised classification (6.14): two baselines, evaluation, and model
selection. Pure — no DB, no network (the embedding model is injected via
`embedding_service`, which itself can wrap a fake for tests). Persistence
lives in app/nlp/classifier_training_db.py; the CLI wires this together
against real data (app/nlp/classifier_training_cli.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer


@dataclass(frozen=True, slots=True)
class TrainingExample:
    licitacion_id: int
    text: str
    label: str
    split: str


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    per_class: dict[str, dict[str, float]]
    confusion_matrix: list[list[int]]
    labels: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "accuracy": self.accuracy, "precision_macro": self.precision_macro,
            "recall_macro": self.recall_macro, "f1_macro": self.f1_macro,
            "per_class": self.per_class, "confusion_matrix": self.confusion_matrix,
            "labels": list(self.labels),
        }


def build_tfidf_logreg_pipeline(random_state: int = 42) -> Pipeline:
    """TF-IDF + logistic regression. `class_weight='balanced'` because the
    real Gold Dataset is heavily skewed toward `not_relevant` (~95%+) —
    without it the model can reach high accuracy by always predicting the
    majority class. Documented, initial heuristic — real tuning is 6.23,
    same spirit as _RULE_SCORE_SATURATION/_SIMILARITY_THRESHOLD."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(min_df=1, ngram_range=(1, 2))),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state)),
    ])


def build_embeddings_logreg_pipeline(embedding_service, random_state: int = 42) -> Pipeline:
    """Linear probe on frozen sentence-transformers embeddings (same model
    as 6.8/6.9, paraphrase-multilingual-MiniLM-L12-v2) — `embedding_service`
    is app.ml.embeddings.EmbeddingService or a test fake with the same
    `.encode(texts) -> np.ndarray` interface."""
    return Pipeline([
        ("embed", FunctionTransformer(embedding_service.encode, validate=False)),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state)),
    ])


def evaluate(pipeline: Pipeline, examples: list[TrainingExample], *, labels: tuple[str, ...]) -> EvaluationResult:
    texts = [example.text for example in examples]
    true_labels = [example.label for example in examples]
    predicted = list(pipeline.predict(texts))

    report = classification_report(
        true_labels, predicted, labels=list(labels), output_dict=True, zero_division=0,
    )
    per_class = {label: report[label] for label in labels}

    return EvaluationResult(
        accuracy=accuracy_score(true_labels, predicted),
        precision_macro=precision_score(true_labels, predicted, labels=list(labels), average="macro", zero_division=0),
        recall_macro=recall_score(true_labels, predicted, labels=list(labels), average="macro", zero_division=0),
        f1_macro=f1_score(true_labels, predicted, labels=list(labels), average="macro", zero_division=0),
        per_class=per_class,
        confusion_matrix=confusion_matrix(true_labels, predicted, labels=list(labels)).tolist(),
        labels=labels,
    )


def train_and_select(
    train: list[TrainingExample], validation: list[TrainingExample], embedding_service, *, random_state: int = 42,
) -> tuple[str, Pipeline, EvaluationResult, EvaluationResult]:
    """Trains both baselines on `train`, evaluates both on `validation`,
    returns (winner_name, winner_pipeline, winner_eval_on_train,
    winner_eval_on_validation). Selection is by f1_macro, not accuracy:
    with a dominant majority class, accuracy stays high (~95%+) regardless
    of whether the model learns anything about the minority classes."""
    labels = tuple(sorted({example.label for example in train} | {example.label for example in validation}))
    train_texts = [example.text for example in train]
    train_labels = [example.label for example in train]

    candidates = {
        "tfidf_logreg": build_tfidf_logreg_pipeline(random_state=random_state),
        "embeddings_logreg": build_embeddings_logreg_pipeline(embedding_service, random_state=random_state),
    }

    results: dict[str, tuple[Pipeline, EvaluationResult, EvaluationResult]] = {}
    for name, pipeline in candidates.items():
        pipeline.fit(train_texts, train_labels)
        train_eval = evaluate(pipeline, train, labels=labels)
        validation_eval = evaluate(pipeline, validation, labels=labels)
        results[name] = (pipeline, train_eval, validation_eval)

    winner_name = max(results, key=lambda name: results[name][2].f1_macro)
    winner_pipeline, winner_train_eval, winner_validation_eval = results[winner_name]
    return winner_name, winner_pipeline, winner_train_eval, winner_validation_eval
