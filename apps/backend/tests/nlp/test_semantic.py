import json
import uuid

import numpy as np

from app.nlp.semantic import EmbeddingsStageExecutor, cosine_similarity
from app.nlp.stages import StageContext
from app.nlp.contracts import ArtifactVersions
from app.nlp.taxonomy import DomainConcept, Taxonomy, TaxonomyCategory, TaxonomySubcategory


def test_cosine_similarity_of_identical_vectors_is_one() -> None:
    vector = np.array([1.0, 2.0, 3.0])

    assert cosine_similarity(vector, vector) == 1.0


def test_cosine_similarity_of_orthogonal_vectors_is_zero() -> None:
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == 0.0


def test_cosine_similarity_handles_zero_vector() -> None:
    assert cosine_similarity(np.array([0.0, 0.0]), np.array([1.0, 0.0])) == 0.0


class FakeRow:
    """Positional access — used for the single-column SELECTs."""

    def __init__(self, *values):
        self._values = values

    def __getitem__(self, index):
        return self._values[index]


class FakeAttrRow:
    """Attribute access — used for the existing-classification lookup,
    which real code reads via `.id`/`.rule_score`/`.category_code`/etc."""

    def __init__(self, **values):
        self._values = values

    def __getattr__(self, name):
        return self._values[name]


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        row = self.first()
        return row[0] if row is not None else None


class FakeEmbeddingService:
    MODEL_NAME = "fake-model"

    def __init__(self, vector_by_marker: dict[str, list[float]], default: list[float]) -> None:
        self._vector_by_marker = vector_by_marker
        self._default = default

    def encode(self, texts) -> np.ndarray:
        vectors = []
        for candidate in texts:
            for marker, vector in self._vector_by_marker.items():
                if marker in candidate.lower():
                    vectors.append(vector)
                    break
            else:
                vectors.append(self._default)
        return np.array(vectors, dtype=np.float32)


class FakeClassifier:
    """Fake sklearn-Pipeline-like object: predicts based on a keyword
    marker in the text, same style as FakeEmbeddingService."""

    def __init__(self, marker: str, label: str, score: float) -> None:
        self._marker = marker
        self._label = label
        self._score = score

    def predict(self, texts):
        return [self._label if self._marker in t.lower() else "not_relevant" for t in texts]

    def predict_proba(self, texts):
        return [[1.0 - self._score, self._score] for _ in texts]


class FakeConnection:
    def __init__(self) -> None:
        self.documents: dict[tuple[int, str], str] = {}
        self.model_versions: dict[tuple[str, str], uuid.UUID] = {}
        self.embeddings: list[dict] = []
        self.classifications: list[dict] = []
        self.categories: dict[tuple[str, str], int] = {}
        self.subcategories: dict[tuple[int, str, str], int] = {}
        self.licitacion_still_open: dict[int, bool] = {}
        self._next_id = 1
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def seed_document(self, licitacion_id: int, content_hash: str, text_value: str) -> None:
        self.documents[(licitacion_id, content_hash)] = text_value

    def seed_licitacion_still_open(self, licitacion_id: int, still_open: bool) -> None:
        self.licitacion_still_open[licitacion_id] = still_open

    def seed_classification(
        self, licitacion_id: int, taxonomy_version: str, *,
        category_code: str | None = None, subcategory_code: str | None = None,
        rule_score: float | None = None, confidence_score: float = 0.0,
    ) -> uuid.UUID:
        category_id = self.categories.setdefault((category_code, taxonomy_version), self._next()) if category_code else None
        subcategory_id = None
        if subcategory_code:
            key = (category_id, subcategory_code, taxonomy_version)
            subcategory_id = self.subcategories.setdefault(key, self._next())
        classification_id = uuid.uuid4()
        self.classifications.append({
            "id": classification_id, "licitacion_id": licitacion_id, "taxonomy_version": taxonomy_version,
            "category_id": category_id, "subcategory_id": subcategory_id, "rule_score": rule_score,
            "confidence_score": confidence_score, "similarity_score": None, "model_score": None,
            "relevance_score": None, "relevance_tier": None,
            "explanation": None, "model_version_id": None, "dataset_version_id": None,
        })
        return classification_id

    def _next(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def _category_code(self, category_id: int | None) -> str | None:
        for (code, _version), cid in self.categories.items():
            if cid == category_id:
                return code
        return None

    def _subcategory_code(self, subcategory_id: int | None) -> str | None:
        for (_category_id, code, _version), sid in self.subcategories.items():
            if sid == subcategory_id:
                return code
        return None

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        upper = sql.upper()
        params = params or {}

        if upper.startswith("SELECT NORMALIZED_TEXT FROM KNOWLEDGE.DOCUMENTS"):
            value = self.documents.get((params["licitacion_id"], params["content_hash"]))
            return FakeResult([FakeRow(value)] if value is not None else [])

        if upper.startswith("SELECT FECHA_CIERRE IS NULL OR FECHA_CIERRE >= NOW() FROM CORE.LICITACION"):
            still_open = self.licitacion_still_open.get(params["licitacion_id"], True)
            return FakeResult([FakeRow(still_open)])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.MODEL_VERSIONS"):
            model_version_id = self.model_versions.get((params["name"], params["version"]))
            return FakeResult([FakeRow(model_version_id)] if model_version_id is not None else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.MODEL_VERSIONS"):
            self.model_versions[(params["name"], params["version"])] = params["id"]
            return FakeResult([])

        if upper.startswith("INSERT INTO KNOWLEDGE.EMBEDDINGS"):
            self.embeddings.append(dict(params))
            return FakeResult([])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.CATEGORIES"):
            category_id = self.categories.get((params["code"], params["taxonomy_version"]))
            return FakeResult([FakeRow(category_id)] if category_id is not None else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.CATEGORIES"):
            category_id = self._next()
            self.categories[(params["code"], params["taxonomy_version"])] = category_id
            return FakeResult([FakeRow(category_id)])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.SUBCATEGORIES"):
            key = (params["category_id"], params["code"], params["taxonomy_version"])
            subcategory_id = self.subcategories.get(key)
            return FakeResult([FakeRow(subcategory_id)] if subcategory_id is not None else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.SUBCATEGORIES"):
            subcategory_id = self._next()
            self.subcategories[(params["category_id"], params["code"], params["taxonomy_version"])] = subcategory_id
            return FakeResult([FakeRow(subcategory_id)])

        if upper.startswith("SELECT CL.ID, CL.RULE_SCORE"):
            matching = [
                c for c in self.classifications
                if c["licitacion_id"] == params["licitacion_id"] and c["taxonomy_version"] == params["taxonomy_version"]
            ]
            if not matching:
                return FakeResult([])
            latest = matching[-1]
            return FakeResult([FakeAttrRow(
                id=latest["id"], rule_score=latest["rule_score"], explanation=latest["explanation"],
                category_code=self._category_code(latest["category_id"]),
                subcategory_code=self._subcategory_code(latest["subcategory_id"]),
            )])

        if upper.startswith("UPDATE KNOWLEDGE.CLASSIFICATIONS"):
            for classification in self.classifications:
                if classification["id"] == params["id"]:
                    classification.update({
                        "category_id": params["category_id"], "subcategory_id": params["subcategory_id"],
                        "similarity_score": params["similarity_score"], "model_score": params["model_score"],
                        "confidence_score": params["confidence_score"],
                        "relevance_score": params["relevance_score"], "relevance_tier": params["relevance_tier"],
                        "model_version_id": params["model_version_id"],
                        "dataset_version_id": params["dataset_version_id"],
                        "explanation": params["explanation"],
                    })
            return FakeResult([])

        if upper.startswith("INSERT INTO KNOWLEDGE.CLASSIFICATIONS"):
            self.classifications.append(dict(params))
            return FakeResult([])

        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def _taxonomy() -> Taxonomy:
    return Taxonomy(
        version="taxonomy-test",
        categories=(
            TaxonomyCategory(
                code="health", name="Salud", description="Salud",
                subcategories=(
                    TaxonomySubcategory(
                        code="geriatric-care", name="Geriatria", description="Geriatria",
                        concepts=(DomainConcept("geriatria", "geriatria", "atencion geriatrica"),),
                    ),
                ),
            ),
            TaxonomyCategory(
                code="construction", name="Construccion", description="Construccion",
                subcategories=(
                    TaxonomySubcategory(code="civil-works", name="Obras", description="Obras", concepts=()),
                ),
            ),
        ),
    )


def _context(licitacion_id: int = 1, text_hash: str = "hash-1") -> StageContext:
    return StageContext(licitacion_id, text_hash, ArtifactVersions("taxonomy-test", "dictionary-test"))


def _embedding_service() -> FakeEmbeddingService:
    return FakeEmbeddingService(
        vector_by_marker={"geriatria": [1.0, 0.0], "irrelevante": [0.0, 1.0]},
        default=[0.0, 0.0],
    )


def test_run_returns_false_when_document_is_missing() -> None:
    connection = FakeConnection()
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    ok = executor.run(_context())

    assert ok is False
    assert connection.embeddings == []


def test_run_persists_embedding_and_creates_classification_above_threshold() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    ok = executor.run(_context())

    assert ok is True
    assert connection.committed is True
    assert len(connection.embeddings) == 1
    [classification] = connection.classifications
    assert classification["similarity_score"] == 1.0
    assert classification["confidence_score"] == 1.0
    assert classification["category_id"] == connection.categories[("health", "taxonomy-test")]


def test_run_below_threshold_leaves_category_unset() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion irrelevante")
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    [classification] = connection.classifications
    assert classification["category_id"] is None
    assert classification["similarity_score"] == 0.0


def test_run_keeps_rule_category_on_a_tied_score() -> None:
    """Regression for the pre-6.15 policy: category no longer always
    comes from rules regardless of confidence — but on a tied score
    (both 1.0 here), the documented tie-break still favors rules
    (combine_signals' precedence, exercised through the real executor)."""
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    classification_id = connection.seed_classification(
        1, "taxonomy-test", category_code="construction", subcategory_code="civil-works",
        rule_score=1.0, confidence_score=1.0,
    )
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    assert len(connection.classifications) == 1
    updated = connection.classifications[0]
    assert updated["id"] == classification_id
    assert updated["similarity_score"] == 1.0
    assert connection._category_code(updated["category_id"]) == "construction"  # rule_score (1.0) ties semantic (1.0), rule wins tie
    assert updated["confidence_score"] == 1.0


def test_run_semantic_wins_when_its_score_is_higher_than_rule() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    connection.seed_classification(
        1, "taxonomy-test", category_code="construction", subcategory_code="civil-works",
        rule_score=0.2, confidence_score=0.2,
    )
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    updated = connection.classifications[0]
    assert connection._category_code(updated["category_id"]) == "health"
    assert updated["confidence_score"] == 1.0


def test_run_reuses_model_version_across_two_licitaciones() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "geriatria")
    connection.seed_document(2, "hash-2", "geriatria")
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context(1, "hash-1"))
    executor.run(_context(2, "hash-2"))

    assert len(connection.model_versions) == 1
    assert connection.embeddings[0]["model_version_id"] == connection.embeddings[1]["model_version_id"]


def test_run_without_classifier_leaves_model_score_zero_and_no_model_version() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion irrelevante")
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    [classification] = connection.classifications
    assert classification["model_score"] == 0.0
    assert classification["model_version_id"] is None


def test_run_persists_model_score_and_wins_when_highest() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion irrelevante")  # no rule/semantic match
    classifier_model_version_id = uuid.uuid4()
    dataset_version_id = uuid.uuid4()
    executor = EmbeddingsStageExecutor(
        lambda: connection, _embedding_service(), taxonomy=_taxonomy(),
        classifier=FakeClassifier(marker="irrelevante", label="health", score=0.8),
        classifier_model_version_id=classifier_model_version_id,
        classifier_dataset_version_id=dataset_version_id,
    )

    executor.run(_context())

    [classification] = connection.classifications
    assert classification["model_score"] == 0.8
    assert connection._category_code(classification["category_id"]) == "health"
    assert classification["confidence_score"] == 0.8
    assert classification["model_version_id"] == classifier_model_version_id
    assert classification["dataset_version_id"] == dataset_version_id
    assert classification["explanation"] is not None


def test_run_model_predicting_not_relevant_does_not_compete() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    executor = EmbeddingsStageExecutor(
        lambda: connection, _embedding_service(), taxonomy=_taxonomy(),
        classifier=FakeClassifier(marker="nunca-matchea", label="health", score=0.9),
    )

    executor.run(_context())

    [classification] = connection.classifications
    assert connection._category_code(classification["category_id"]) == "health"  # semantic wins, model had no match


def test_run_persists_relevance_score_and_tier_for_open_licitacion() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    connection.seed_licitacion_still_open(1, True)
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    [classification] = connection.classifications
    assert classification["relevance_score"] == 1.0
    assert classification["relevance_tier"] == "high"
    assert json.loads(classification["explanation"])["relevance"]["still_open"] is True


def test_run_discounts_relevance_score_for_closed_licitacion() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    connection.seed_licitacion_still_open(1, False)
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    [classification] = connection.classifications
    assert classification["relevance_score"] == 0.5
    assert classification["relevance_tier"] == "medium"
    assert json.loads(classification["explanation"])["relevance"]["still_open"] is False


def test_run_relevance_score_zero_and_not_relevant_when_no_signal_matches() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion irrelevante")
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    [classification] = connection.classifications
    assert classification["relevance_score"] == 0.0
    assert classification["relevance_tier"] == "not_relevant"


def test_run_explanation_keeps_matched_rules_hybrid_and_relevance_together() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion sobre geriatria")
    connection.seed_classification(
        1, "taxonomy-test", category_code="health", subcategory_code="geriatric-care",
        rule_score=1.0, confidence_score=1.0,
    )
    connection.classifications[0]["explanation"] = {"matched_rules": [{"keyword": "geriatria"}]}
    executor = EmbeddingsStageExecutor(lambda: connection, _embedding_service(), taxonomy=_taxonomy())

    executor.run(_context())

    explanation = json.loads(connection.classifications[0]["explanation"])
    assert "matched_rules" in explanation
    assert "hybrid" in explanation
    assert "relevance" in explanation
