import json

from app.nlp.classification import ClassificationStageExecutor
from app.nlp.dictionary import DictionaryEntry, DomainDictionary, DomainTheme
from app.nlp.stages import StageContext
from app.nlp.contracts import ArtifactVersions
from app.nlp.taxonomy import DomainConcept, Taxonomy, TaxonomyCategory, TaxonomySubcategory


class FakeRow:
    def __init__(self, value):
        self._value = value

    def __getitem__(self, index):
        return self._value


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self) -> None:
        self.documents: dict[tuple[int, str], str] = {}
        self.categories: dict[tuple[str, str], int] = {}
        self.subcategories: dict[tuple[int, str, str], int] = {}
        self.rules: dict[tuple[str, str], dict] = {}
        self.classifications: list[dict] = []
        self._next_id = 1
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def seed_document(self, licitacion_id: int, content_hash: str, normalized_text: str) -> None:
        self.documents[(licitacion_id, content_hash)] = normalized_text

    def _next(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        upper = sql.upper()
        params = params or {}

        if upper.startswith("SELECT NORMALIZED_TEXT FROM KNOWLEDGE.DOCUMENTS"):
            text_value = self.documents.get((params["licitacion_id"], params["content_hash"]))
            return FakeResult([FakeRow(text_value)] if text_value is not None else [])

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
            key = (params["category_id"], params["code"], params["taxonomy_version"])
            self.subcategories[key] = subcategory_id
            return FakeResult([FakeRow(subcategory_id)])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.RULES"):
            rule = self.rules.get((params["code"], params["version"]))
            return FakeResult([FakeRow(rule["id"])] if rule else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.RULES"):
            self.rules[(params["code"], params["version"])] = dict(params)
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
                        concepts=(DomainConcept("geriatria", "Geriatria", "Geriatria"),),
                    ),
                ),
            ),
        ),
    )


def _dictionary() -> DomainDictionary:
    return DomainDictionary(
        version="dictionary-test",
        entries=(
            DictionaryEntry(concept="geriatria_termino", theme=DomainTheme.GERIATRIA, term="geriatria"),
        ),
    )


def _context(licitacion_id: int = 1, text_hash: str = "hash-1") -> StageContext:
    return StageContext(licitacion_id, text_hash, ArtifactVersions("taxonomy-test", "dictionary-test"))


def test_run_returns_false_when_document_is_missing() -> None:
    connection = FakeConnection()
    executor = ClassificationStageExecutor(lambda: connection, dictionary=_dictionary(), taxonomy=_taxonomy())

    ok = executor.run(_context())

    assert ok is False
    assert connection.classifications == []
    assert connection.closed is True


def test_run_persists_classification_with_matched_category_and_subcategory() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "licitacion para atencion geriatria integral")
    executor = ClassificationStageExecutor(lambda: connection, dictionary=_dictionary(), taxonomy=_taxonomy())

    ok = executor.run(_context())

    assert ok is True
    assert connection.committed is True
    [classification] = connection.classifications
    assert classification["licitacion_id"] == 1
    assert classification["taxonomy_version"] == "taxonomy-test"
    assert classification["rule_score"] == 1.0
    assert classification["confidence_score"] == 1.0 / 3.0
    assert classification["category_id"] == connection.categories[("health", "taxonomy-test")]
    assert classification["subcategory_id"] is not None
    explanation = json.loads(classification["explanation"])
    assert explanation["matched_rules"][0]["concept_code"] == "geriatria"


def test_run_creates_the_rule_row_used_for_the_match() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "geriatria")
    executor = ClassificationStageExecutor(lambda: connection, dictionary=_dictionary(), taxonomy=_taxonomy())

    executor.run(_context())

    assert len(connection.rules) == 1
    ((code, version), rule) = next(iter(connection.rules.items()))
    assert version == "dictionary-test"
    assert rule["rule_type"] == "keyword"


def test_run_with_no_rule_match_still_persists_with_null_category() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "texto sin relacion alguna")
    executor = ClassificationStageExecutor(lambda: connection, dictionary=_dictionary(), taxonomy=_taxonomy())

    ok = executor.run(_context())

    assert ok is True
    [classification] = connection.classifications
    assert classification["category_id"] is None
    assert classification["subcategory_id"] is None
    assert classification["confidence_score"] == 0.0


def test_run_reuses_existing_category_across_two_licitaciones() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "geriatria")
    connection.seed_document(2, "hash-2", "geriatria")
    executor = ClassificationStageExecutor(lambda: connection, dictionary=_dictionary(), taxonomy=_taxonomy())

    executor.run(_context(1, "hash-1"))
    executor.run(_context(2, "hash-2"))

    assert len(connection.categories) == 1
    assert connection.classifications[0]["category_id"] == connection.classifications[1]["category_id"]
