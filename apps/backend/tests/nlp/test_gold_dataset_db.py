import uuid

from app.nlp.gold_dataset_db import (
    count_pending_labels, create_dataset_version, ensure_documents, fetch_labeled_rows,
    fetch_pending_labels, fetch_training_rows, finalize_dataset_version, insert_pending_labels,
    save_label, save_splits,
)


class FakeRow:
    def __init__(self, **values):
        self._values = values

    def __getattr__(self, name):
        return self._values[name]

    def __getitem__(self, index):
        return list(self._values.values())[index]


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class FakeConnection:
    def __init__(self) -> None:
        self.dataset_versions: dict[uuid.UUID, dict] = {}
        self.gold_labels: dict[tuple, dict] = {}
        self.licitaciones = {
            1: {"codigo": "COD-1", "nombre": "Silla de ruedas", "descripcion": "desc", "monto_estimado": 100, "organismo": "SENAMA"},
            2: {"codigo": "COD-2", "nombre": "Papel oficio", "descripcion": None, "monto_estimado": None, "organismo": None},
        }
        self.categories = {1: "health", 2: "construction"}
        self.subcategories = {5: 1, 6: 2}  # subcategory_id -> category_id
        self.documents: dict[int, dict] = {}
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        upper = sql.upper()
        params = params or {}

        if upper.startswith("INSERT INTO KNOWLEDGE.DATASET_VERSIONS"):
            self.dataset_versions[params["id"]] = dict(params)
            return FakeResult([])

        if upper.startswith("INSERT INTO KNOWLEDGE.GOLD_LABELS"):
            key = (params["dataset_version_id"], params["licitacion_id"])
            self.gold_labels[key] = {
                "id": params["id"], "dataset_version_id": params["dataset_version_id"],
                "licitacion_id": params["licitacion_id"], "relevant": None, "category_id": None,
                "subcategory_id": None, "split": None,
            }
            return FakeResult([])

        if upper.startswith("SELECT GL.LICITACION_ID, L.CODIGO"):
            rows = []
            for (dataset_version_id, licitacion_id), row in self.gold_labels.items():
                if dataset_version_id != params["dataset_version_id"] or row["relevant"] is not None:
                    continue
                lic = self.licitaciones[licitacion_id]
                rows.append(FakeRow(licitacion_id=licitacion_id, codigo=lic["codigo"], nombre=lic["nombre"],
                                     descripcion=lic["descripcion"], monto_estimado=lic["monto_estimado"],
                                     organismo=lic["organismo"]))
            return FakeResult(rows)

        if upper.startswith("SELECT NOMBRE FROM CORE.LICITACION_ITEM"):
            return FakeResult([])

        if upper.startswith("UPDATE KNOWLEDGE.GOLD_LABELS SET RELEVANT"):
            key = (params["dataset_version_id"], params["licitacion_id"])
            self.gold_labels[key].update({
                "relevant": params["relevant"], "category_id": params["category_id"],
                "subcategory_id": params["subcategory_id"], "labeled_by": params["labeled_by"],
                "notes": params["notes"],
            })
            return FakeResult([])

        if upper.startswith("SELECT GL.LICITACION_ID, GL.RELEVANT"):
            rows = []
            for (dataset_version_id, licitacion_id), row in self.gold_labels.items():
                if dataset_version_id != params["dataset_version_id"] or row["relevant"] is None:
                    continue
                category_code = self.categories.get(row["category_id"])
                subcategory_category_id = self.subcategories.get(row["subcategory_id"])
                rows.append(FakeRow(
                    licitacion_id=licitacion_id, relevant=row["relevant"], category_id=row["category_id"],
                    category_code=category_code, subcategory_id=row["subcategory_id"],
                    subcategory_category_id=subcategory_category_id, split=row["split"],
                    labeled_by=row.get("labeled_by"),
                ))
            return FakeResult(rows)

        if upper.startswith("SELECT COUNT(*) FROM KNOWLEDGE.GOLD_LABELS"):
            count = sum(
                1 for (dvid, _), row in self.gold_labels.items()
                if dvid == params["dataset_version_id"] and row["relevant"] is None
            )
            return FakeResult([FakeRow(count=count)])

        if upper.startswith("UPDATE KNOWLEDGE.GOLD_LABELS SET SPLIT"):
            key = (params["dataset_version_id"], params["licitacion_id"])
            self.gold_labels[key]["split"] = params["split"]
            return FakeResult([])

        if upper.startswith("UPDATE KNOWLEDGE.DATASET_VERSIONS"):
            self.dataset_versions[params["id"]].update(params)
            return FakeResult([])

        if upper.startswith("SELECT 1 FROM KNOWLEDGE.DOCUMENTS"):
            exists = params["licitacion_id"] in self.documents
            return FakeResult([FakeRow(exists=1)] if exists else [])

        if upper.startswith("SELECT NOMBRE, DESCRIPCION FROM CORE.LICITACION"):
            lic = self.licitaciones.get(params["licitacion_id"])
            return FakeResult([FakeRow(nombre=lic["nombre"], descripcion=lic["descripcion"])] if lic else [])

        if upper.startswith("INSERT INTO KNOWLEDGE.DOCUMENTS"):
            self.documents[params["licitacion_id"]] = {"normalized_text": params["normalized_text"]}
            return FakeResult([])

        if upper.startswith("SELECT DISTINCT ON (GL.LICITACION_ID)"):
            rows = []
            for (dataset_version_id, licitacion_id), row in self.gold_labels.items():
                if dataset_version_id != params["dataset_version_id"] or row["relevant"] is None:
                    continue
                category_code = self.categories.get(row["category_id"])
                doc = self.documents.get(licitacion_id, {})
                rows.append(FakeRow(
                    licitacion_id=licitacion_id, relevant=row["relevant"], category_code=category_code,
                    split=row["split"], normalized_text=doc.get("normalized_text"),
                ))
            return FakeResult(rows)

        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self) -> None:
        self.committed = True


def test_create_dataset_version_and_fetch_pending() -> None:
    connection = FakeConnection()
    dataset_version_id = create_dataset_version(
        connection, name="gold-dataset", version="2026.1", taxonomy_version="taxonomy-2026.2", manifest={"status": "pending_labels"},
    )
    insert_pending_labels(connection, dataset_version_id, [1, 2])

    pending = fetch_pending_labels(connection, dataset_version_id)

    assert {row["licitacion_id"] for row in pending} == {1, 2}
    assert count_pending_labels(connection, dataset_version_id) == 2


def test_save_label_removes_row_from_pending() -> None:
    connection = FakeConnection()
    dataset_version_id = create_dataset_version(
        connection, name="gold-dataset", version="2026.1", taxonomy_version="taxonomy-2026.2", manifest={},
    )
    insert_pending_labels(connection, dataset_version_id, [1])

    save_label(
        connection, dataset_version_id, 1, relevant=True, category_id=1, subcategory_id=5,
        taxonomy_version="taxonomy-2026.2", labeled_by="tester@example.com", notes=None,
    )

    assert count_pending_labels(connection, dataset_version_id) == 0
    labeled = fetch_labeled_rows(connection, dataset_version_id)
    assert labeled[0]["category_code"] == "health"
    assert labeled[0]["subcategory_category_id"] == 1


def test_save_splits_and_finalize() -> None:
    connection = FakeConnection()
    dataset_version_id = create_dataset_version(
        connection, name="gold-dataset", version="2026.1", taxonomy_version="taxonomy-2026.2", manifest={},
    )
    insert_pending_labels(connection, dataset_version_id, [1, 2])
    save_label(
        connection, dataset_version_id, 1, relevant=True, category_id=1, subcategory_id=5,
        taxonomy_version="taxonomy-2026.2", labeled_by="tester@example.com", notes=None,
    )
    save_label(
        connection, dataset_version_id, 2, relevant=False, category_id=None, subcategory_id=None,
        taxonomy_version="taxonomy-2026.2", labeled_by="tester@example.com", notes="not relevant",
    )

    save_splits(connection, dataset_version_id, {1: "train", 2: "test"})
    labeled = fetch_labeled_rows(connection, dataset_version_id)
    assert {row["split"] for row in labeled} == {"train", "test"}

    finalize_dataset_version(connection, dataset_version_id, record_count=2, manifest={"status": "ready"})
    assert connection.dataset_versions[dataset_version_id]["record_count"] == 2


def test_ensure_documents_creates_missing_and_skips_existing() -> None:
    connection = FakeConnection()

    ensure_documents(connection, [1, 2])

    assert 1 in connection.documents
    assert 2 in connection.documents
    assert "silla de ruedas" in connection.documents[1]["normalized_text"]

    connection.documents[1]["normalized_text"] = "sentinel-unchanged"
    ensure_documents(connection, [1])
    assert connection.documents[1]["normalized_text"] == "sentinel-unchanged"


def test_fetch_training_rows_returns_label_and_text() -> None:
    connection = FakeConnection()
    dataset_version_id = create_dataset_version(
        connection, name="gold-dataset", version="2026.1", taxonomy_version="taxonomy-2026.2", manifest={},
    )
    insert_pending_labels(connection, dataset_version_id, [1, 2])
    save_label(
        connection, dataset_version_id, 1, relevant=True, category_id=1, subcategory_id=5,
        taxonomy_version="taxonomy-2026.2", labeled_by="tester@example.com", notes=None,
    )
    save_label(
        connection, dataset_version_id, 2, relevant=False, category_id=None, subcategory_id=None,
        taxonomy_version="taxonomy-2026.2", labeled_by="tester@example.com", notes=None,
    )
    save_splits(connection, dataset_version_id, {1: "train", 2: "test"})
    ensure_documents(connection, [1, 2])

    rows = fetch_training_rows(connection, dataset_version_id)

    by_id = {row["licitacion_id"]: row for row in rows}
    assert by_id[1]["label"] == "health"
    assert by_id[1]["split"] == "train"
    assert "silla de ruedas" in by_id[1]["text"]
    assert by_id[2]["label"] == "not_relevant"
