import numpy as np

from app.nlp.classifier_training import (
    TrainingExample, build_embeddings_logreg_pipeline, build_tfidf_logreg_pipeline, evaluate, train_and_select,
)


class _ConstantEmbeddingService:
    """Every text maps to the same vector -- embeddings carry zero signal,
    so a classifier trained on them can only ever predict the majority
    class. Used to deterministically force tfidf_logreg to win
    train_and_select (a legitimate, non-contrived case: when one feature
    space has no signal, the other should be selected)."""

    def encode(self, texts):
        texts = list(texts)
        return np.ones((len(texts), 4), dtype=np.float32)


class _WordCountEmbeddingService:
    """A real (if crude) text feature: normalized bag-of-words counts over
    a tiny fixed vocabulary — informative, so embeddings_logreg can learn
    from it like a real embedding would."""

    _VOCAB = ("salud", "geriatria", "asfalto", "camion")

    def encode(self, texts):
        rows = []
        for text in texts:
            lowered = text.casefold()
            rows.append([float(word in lowered) for word in self._VOCAB])
        return np.array(rows, dtype=np.float32)


_HEALTH_TEXTS = [
    "adquisicion de sillas de ruedas para geriatria",
    "suministro de ayudas tecnicas para adultos mayores salud",
    "compra de andadores para pacientes salud geriatria",
    "insumos de rehabilitacion geriatrica salud",
]
_NOT_RELEVANT_TEXTS = [
    "suministro de asfalto para camino rural",
    "mantencion de camiones municipales asfalto",
    "compra de asfalto para pavimentacion",
    "arriendo de camion para transporte de aridos",
]


def _examples(texts: list[str], label: str, split: str, start_id: int) -> list[TrainingExample]:
    return [
        TrainingExample(licitacion_id=start_id + i, text=text, label=label, split=split)
        for i, text in enumerate(texts)
    ]


def _dataset(split: str, start_id: int) -> list[TrainingExample]:
    return _examples(_HEALTH_TEXTS, "health", split, start_id) + _examples(_NOT_RELEVANT_TEXTS, "not_relevant", split, start_id + 100)


def test_tfidf_pipeline_trains_and_predicts() -> None:
    pipeline = build_tfidf_logreg_pipeline()
    train = _dataset("train", 1)

    pipeline.fit([e.text for e in train], [e.label for e in train])
    predictions = pipeline.predict([e.text for e in train])

    assert set(predictions) <= {"health", "not_relevant"}


def test_embeddings_pipeline_trains_and_predicts() -> None:
    pipeline = build_embeddings_logreg_pipeline(_WordCountEmbeddingService())
    train = _dataset("train", 1)

    pipeline.fit([e.text for e in train], [e.label for e in train])
    predictions = pipeline.predict([e.text for e in train])

    assert set(predictions) <= {"health", "not_relevant"}


def test_evaluate_computes_perfect_metrics_for_a_perfect_classifier() -> None:
    examples = _dataset("test", 1)
    label_by_text = {e.text: e.label for e in examples}

    class _PerfectPipeline:
        def predict(self, texts):
            return [label_by_text[t] for t in texts]

    result = evaluate(_PerfectPipeline(), examples, labels=("health", "not_relevant"))

    assert result.accuracy == 1.0
    assert result.f1_macro == 1.0
    assert result.confusion_matrix == [[4, 0], [0, 4]]


def test_evaluate_handles_a_label_absent_from_the_split() -> None:
    class _AlwaysNotRelevant:
        def predict(self, texts):
            return ["not_relevant" for _ in texts]

    examples = _examples(_NOT_RELEVANT_TEXTS, "not_relevant", "test", 1)

    result = evaluate(_AlwaysNotRelevant(), examples, labels=("construction", "health", "not_relevant"))

    assert result.per_class["construction"]["support"] == 0
    assert result.per_class["health"]["support"] == 0
    assert result.per_class["not_relevant"]["recall"] == 1.0


def test_train_and_select_picks_tfidf_when_embeddings_carry_no_signal() -> None:
    train = _dataset("train", 1)
    validation = _dataset("validation", 1000)

    winner_name, winner_pipeline, train_eval, validation_eval = train_and_select(
        train, validation, _ConstantEmbeddingService(),
    )

    assert winner_name == "tfidf_logreg"
    assert validation_eval.f1_macro > 0.5
    assert winner_pipeline.predict(["adquisicion sillas de ruedas geriatria"])[0] == "health"


def test_train_and_select_returns_a_valid_candidate_name() -> None:
    train = _dataset("train", 1)
    validation = _dataset("validation", 1000)

    winner_name, _, _, validation_eval = train_and_select(train, validation, _WordCountEmbeddingService())

    assert winner_name in {"tfidf_logreg", "embeddings_logreg"}
    assert 0.0 <= validation_eval.f1_macro <= 1.0
