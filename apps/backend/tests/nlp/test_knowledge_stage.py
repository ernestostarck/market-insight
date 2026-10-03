import uuid

from app.nlp.knowledge_stage import KnowledgeStageExecutor
from app.nlp.stages import StageContext
from app.nlp.contracts import ArtifactVersions


class FakeRow:
    def __init__(self, *values):
        self._values = values

    def __getitem__(self, index):
        return self._values[index]

    def __iter__(self):
        return iter(self._values)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class FakeConnection:
    def __init__(self) -> None:
        self.documents: dict[tuple[int, str], str] = {}
        self.organismos: dict[int, tuple[str, str | None, str | None]] = {}
        self.items: dict[int, list[dict]] = {}
        self.classifications: dict[tuple[int, str], uuid.UUID] = {}
        self.entities: list[dict] = []
        self.categories: dict[tuple[str, str], int] = {}
        self.subcategories: dict[tuple[int, str, str], int] = {}
        self.product_concepts: dict[tuple[str, str], int] = {}
        self.products: list[dict] = []
        self._next_id = 1
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def seed_document(self, licitacion_id: int, content_hash: str, text_value: str) -> None:
        self.documents[(licitacion_id, content_hash)] = text_value

    def seed_organismo(self, licitacion_id: int, nombre: str, region: str | None = None, comuna: str | None = None) -> None:
        self.organismos[licitacion_id] = (nombre, region, comuna)

    def seed_items(self, licitacion_id: int, *nombres: str) -> None:
        self.items[licitacion_id] = [
            {"id": index + 1, "nombre": nombre, "descripcion": None, "cantidad": None, "unidad": None}
            for index, nombre in enumerate(nombres)
        ]

    def seed_item(
        self, licitacion_id: int, item_id: int, nombre: str, descripcion: str | None = None,
        cantidad: float | None = None, unidad: str | None = None,
    ) -> None:
        self.items.setdefault(licitacion_id, []).append(
            {"id": item_id, "nombre": nombre, "descripcion": descripcion, "cantidad": cantidad, "unidad": unidad}
        )

    def seed_classification(self, licitacion_id: int, taxonomy_version: str) -> uuid.UUID:
        classification_id = uuid.uuid4()
        self.classifications[(licitacion_id, taxonomy_version)] = classification_id
        return classification_id

    def _next(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        upper = sql.upper()
        params = params or {}

        if upper.startswith("SELECT NORMALIZED_TEXT FROM KNOWLEDGE.DOCUMENTS"):
            value = self.documents.get((params["licitacion_id"], params["content_hash"]))
            return FakeResult([FakeRow(value)] if value is not None else [])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.CLASSIFICATIONS"):
            classification_id = self.classifications.get((params["licitacion_id"], params["taxonomy_version"]))
            return FakeResult([FakeRow(classification_id)] if classification_id is not None else [])

        if upper.startswith("SELECT O.NOMBRE, O.REGION, O.COMUNA"):
            organismo = self.organismos.get(params["licitacion_id"])
            return FakeResult([FakeRow(*organismo)] if organismo is not None else [])

        if upper.startswith("SELECT ID, NOMBRE, DESCRIPCION, CANTIDAD, UNIDAD FROM CORE.LICITACION_ITEM"):
            rows = self.items.get(params["licitacion_id"], [])
            return FakeResult([FakeRow(r["id"], r["nombre"], r["descripcion"], r["cantidad"], r["unidad"]) for r in rows])

        if upper.startswith("INSERT INTO KNOWLEDGE.ENTITIES"):
            self.entities.append(dict(params))
            return FakeResult([])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.CATEGORIES"):
            category_id = self.categories.get((params["code"], params["taxonomy_version"]))
            return FakeResult([FakeRow(category_id)] if category_id is not None else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.CATEGORIES"):
            category_id = self._next()
            self.categories[(params["code"], params["taxonomy_version"])] = category_id
            return FakeResult([FakeRow(category_id)])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.SUBCATEGORIES"):
            subcategory_id = self.subcategories.get((params["category_id"], params["code"], params["taxonomy_version"]))
            return FakeResult([FakeRow(subcategory_id)] if subcategory_id is not None else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.SUBCATEGORIES"):
            subcategory_id = self._next()
            self.subcategories[(params["category_id"], params["code"], params["taxonomy_version"])] = subcategory_id
            return FakeResult([FakeRow(subcategory_id)])

        if upper.startswith("SELECT ID FROM KNOWLEDGE.PRODUCT_CONCEPTS"):
            product_concept_id = self.product_concepts.get((params["code"], params["dictionary_version"]))
            return FakeResult([FakeRow(product_concept_id)] if product_concept_id is not None else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.PRODUCT_CONCEPTS"):
            product_concept_id = self._next()
            self.product_concepts[(params["code"], params["dictionary_version"])] = product_concept_id
            return FakeResult([FakeRow(product_concept_id)])

        if upper.startswith("INSERT INTO KNOWLEDGE.PRODUCTS"):
            key = (params["licitacion_item_id"], params["product_concept_id"])
            if not any((p["licitacion_item_id"], p["product_concept_id"]) == key for p in self.products):
                self.products.append(dict(params))
            return FakeResult([])

        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def _context(licitacion_id: int = 1, text_hash: str = "hash-1", taxonomy_version: str = "taxonomy-test") -> StageContext:
    return StageContext(licitacion_id, text_hash, ArtifactVersions(taxonomy_version, "dictionary-test"))


def test_run_returns_false_when_document_is_missing() -> None:
    connection = FakeConnection()
    executor = KnowledgeStageExecutor(lambda: connection)

    assert executor.run(_context()) is False
    assert connection.entities == []


def test_run_persists_structured_and_text_entities() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "se requieren 50 kg marca Invacare")
    connection.seed_organismo(1, "Servicio Nacional", region="Metropolitana", comuna="Santiago")
    connection.seed_items(1, "Silla de ruedas", "Rampa de acceso")

    ok = KnowledgeStageExecutor(lambda: connection).run(_context())

    assert ok is True
    assert connection.committed is True
    by_type = {}
    for row in connection.entities:
        by_type.setdefault(row["entity_type"], []).append(row)
    assert by_type["organismo"][0]["value"] == "Servicio Nacional"
    assert by_type["organismo"][0]["confidence_score"] == 1.0
    assert by_type["ubicacion"][0]["value"] == "Santiago, Metropolitana"
    assert {row["value"] for row in by_type["producto"]} == {"Silla de ruedas", "Rampa de acceso"}
    assert by_type["cantidad"][0]["value"] == "50 kg"
    assert by_type["marca"][0]["value"] == "Invacare"


def test_run_links_the_latest_classification_id() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "sin entidades de texto aqui")
    connection.seed_organismo(1, "Servicio Nacional")
    classification_id = connection.seed_classification(1, "taxonomy-test")

    KnowledgeStageExecutor(lambda: connection).run(_context())

    assert all(row["classification_id"] == classification_id for row in connection.entities)


def test_run_without_organismo_or_items_still_succeeds() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "texto sin marcas ni cantidades")

    ok = KnowledgeStageExecutor(lambda: connection).run(_context())

    assert ok is True
    assert connection.entities == []


def test_run_without_region_or_comuna_skips_ubicacion() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "texto")
    connection.seed_organismo(1, "Servicio Nacional")

    KnowledgeStageExecutor(lambda: connection).run(_context())

    assert [row for row in connection.entities if row["entity_type"] == "ubicacion"] == []


def test_run_persists_matched_product_with_attributes() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "sin entidades relevantes en el documento")
    connection.seed_item(
        1, item_id=42, nombre="Silla de ruedas",
        descripcion="silla de ruedas marca Invacare, acero inoxidable, 60 cm x 40 cm x 90 cm, capacidad 120 kg, plegable",
        cantidad=3, unidad="unidades",
    )

    ok = KnowledgeStageExecutor(lambda: connection).run(_context())

    assert ok is True
    assert len(connection.products) == 1
    product = connection.products[0]
    assert product["licitacion_item_id"] == 42
    assert product["cantidad"] == 3
    assert product["unidad"] == "unidades"
    assert "acero inoxidable" in product["materiales"]
    assert product["dimensiones"] == "60 cm x 40 cm x 90 cm"
    assert product["capacidad"] == "120 kg"
    assert "plegable" in product["caracteristicas_tecnicas"]
    assert product["confidence_score"] == 1.0
    assert product["product_concept_id"] in connection.product_concepts.values()


def test_run_without_known_product_creates_no_product_row() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "texto")
    connection.seed_item(1, item_id=1, nombre="Servicio de aseo general")

    ok = KnowledgeStageExecutor(lambda: connection).run(_context())

    assert ok is True
    assert connection.products == []


def test_run_does_not_duplicate_product_rows_on_reprocessing() -> None:
    connection = FakeConnection()
    connection.seed_document(1, "hash-1", "texto")
    connection.seed_item(1, item_id=42, nombre="Silla de ruedas")

    KnowledgeStageExecutor(lambda: connection).run(_context())
    connection.entities.clear()
    KnowledgeStageExecutor(lambda: connection).run(_context())

    assert len(connection.products) == 1
