import json
import uuid

from app.nlp.human_review_db import (
    fetch_review_history,
    fetch_review_queue,
    get_review_statistics,
    incorporate_feedback_to_gold_dataset,
    record_human_review,
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

    def scalar(self):
        first = self.first()
        if first is None:
            return None
        if hasattr(first, "_values"):
            return list(first._values.values())[0]
        return first[0]


class FakeDB:
    def __init__(self) -> None:
        self.users = {
            uuid.UUID("11111111-1111-1111-1111-111111111111"): {"email": "evaluator@test.cl"},
        }
        self.licitaciones = {
            101: {
                "codigo": "101-1-LE26",
                "nombre": "Sillas de ruedas manuales",
                "descripcion": "Adquisicion de sillas",
                "monto_estimado": 5000000,
                "organismo": "SENAMA",
            },
            102: {
                "codigo": "102-2-LE26",
                "nombre": "Servicio de transporte",
                "descripcion": "Transporte general",
                "monto_estimado": 2000000,
                "organismo": "MOP",
            },
        }
        self.categories = {1: "health", 2: "construction"}
        self.subcategories = {11: ("health", "geriatric-care"), 21: ("construction", "accessibility-adaptation")}
        self.items = {
            101: ["Silla de ruedas estándar"],
            102: ["Servicio de traslado"],
        }
        self.classifications: dict[uuid.UUID, dict] = {
            uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"): {
                "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                "licitacion_id": 101,
                "category_id": 1,
                "subcategory_id": 11,
                "taxonomy_version": "taxonomy-2026.2",
                "confidence_score": 0.50,  # low confidence
                "rule_score": 0.50,
                "similarity_score": 0.48,
                "model_score": None,
                "relevance_score": 0.70,
                "relevance_tier": "high",
                "explanation": {
                    "hybrid": {
                        "scores": {"rule": 0.50, "semantic": 0.48},
                        "categories": {"rule": "health", "semantic": "health"},
                        "winning_method": "rule",
                    }
                },
            },
            uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"): {
                "id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                "licitacion_id": 102,
                "category_id": 1,
                "subcategory_id": None,
                "taxonomy_version": "taxonomy-2026.2",
                "confidence_score": 0.72,
                "rule_score": 0.72,
                "similarity_score": 0.70,
                "model_score": None,
                "relevance_score": 0.65,
                "relevance_tier": "medium",
                "explanation": {
                    "hybrid": {
                        "scores": {"rule": 0.72, "semantic": 0.70},
                        "categories": {"rule": "health", "semantic": "construction"},  # conflicting!
                        "winning_method": "rule",
                    }
                },
            },
        }
        self.human_reviews: dict[uuid.UUID, dict] = {}
        self.gold_labels: dict[tuple, dict] = {}
        self.dataset_versions: dict[uuid.UUID, dict] = {
            uuid.UUID("99999999-9999-9999-9999-999999999999"): {
                "id": uuid.UUID("99999999-9999-9999-9999-999999999999"),
                "record_count": 0,
                "manifest": json.dumps({"status": "ready"}),
            }
        }
        self.documents: dict[int, dict] = {}

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        upper = sql.upper()
        params = params or {}

        # 1. Base classifications query for review queue
        if upper.startswith("SELECT C.ID AS CLASSIFICATION_ID, C.LICITACION_ID"):
            rows = []
            for cl_id, cl in self.classifications.items():
                if "WHERE HR.ID IS NULL" in upper:
                    # check if reviewed
                    already_reviewed = any(r["classification_id"] == cl_id for r in self.human_reviews.values())
                    if already_reviewed:
                        continue
                lic = self.licitaciones.get(cl["licitacion_id"], {})
                cat_code = self.categories.get(cl["category_id"])
                sub_code = self.subcategories.get(cl["subcategory_id"], (None, None))[1]
                rows.append(
                    FakeRow(
                        classification_id=cl["id"],
                        licitacion_id=cl["licitacion_id"],
                        category_id=cl["category_id"],
                        category_code=cat_code,
                        subcategory_id=cl["subcategory_id"],
                        subcategory_code=sub_code,
                        confidence_score=cl["confidence_score"],
                        rule_score=cl["rule_score"],
                        similarity_score=cl["similarity_score"],
                        model_score=cl["model_score"],
                        relevance_score=cl["relevance_score"],
                        relevance_tier=cl["relevance_tier"],
                        explanation=cl["explanation"],
                        codigo=lic.get("codigo"),
                        nombre=lic.get("nombre"),
                        descripcion=lic.get("descripcion"),
                        monto_estimado=lic.get("monto_estimado"),
                        organismo=lic.get("organismo"),
                    )
                )
            return FakeResult(rows)

        # 2. Items query
        if upper.startswith("SELECT NOMBRE FROM CORE.LICITACION_ITEM"):
            lic_id = params.get("licitacion_id")
            item_list = self.items.get(lic_id, [])
            return FakeResult([FakeRow(nombre=name) for name in item_list])

        # 3. Check existing human review
        if upper.startswith("SELECT ID FROM KNOWLEDGE.HUMAN_REVIEWS WHERE CLASSIFICATION_ID"):
            cl_id = params["classification_id"]
            rev_id = params["reviewer_id"]
            for r in self.human_reviews.values():
                if r["classification_id"] == cl_id and r["reviewer_id"] == rev_id:
                    return FakeResult([FakeRow(id=r["id"])])
            return FakeResult([])

        # 4. Insert human review
        if upper.startswith("INSERT INTO KNOWLEDGE.HUMAN_REVIEWS"):
            self.human_reviews[params["id"]] = dict(params)
            return FakeResult([])

        # 5. Update human review
        if upper.startswith("UPDATE KNOWLEDGE.HUMAN_REVIEWS SET"):
            rev_id = params["id"]
            if rev_id in self.human_reviews:
                self.human_reviews[rev_id].update(params)
            return FakeResult([])

        # 6. Select classification for merge
        if upper.startswith("SELECT CATEGORY_ID, SUBCATEGORY_ID, EXPLANATION, RELEVANCE_SCORE FROM KNOWLEDGE.CLASSIFICATIONS"):
            cl_id = params["id"]
            cl = self.classifications.get(cl_id)
            if cl:
                return FakeResult([
                    FakeRow(
                        category_id=cl["category_id"],
                        subcategory_id=cl["subcategory_id"],
                        explanation=cl["explanation"],
                        relevance_score=cl["relevance_score"],
                    )
                ])
            return FakeResult([])

        # 7. Update classification
        if upper.startswith("UPDATE KNOWLEDGE.CLASSIFICATIONS SET"):
            cl_id = params["id"]
            if cl_id in self.classifications:
                self.classifications[cl_id]["category_id"] = params["category_id"]
                self.classifications[cl_id]["subcategory_id"] = params["subcategory_id"]
                self.classifications[cl_id]["confidence_score"] = 1.0
                self.classifications[cl_id]["relevance_tier"] = params["relevance_tier"]
                self.classifications[cl_id]["explanation"] = json.loads(params["explanation"])
            return FakeResult([])

        # 8. Fetch review history
        if upper.startswith("SELECT HR.ID, HR.CLASSIFICATION_ID, HR.REVIEWER_ID, U.EMAIL AS REVIEWER_EMAIL") and "L.CODIGO, L.NOMBRE" in upper:
            rows = []
            for r in self.human_reviews.values():
                u = self.users.get(r["reviewer_id"], {"email": "unknown"})
                cl = self.classifications.get(r["classification_id"], {})
                lic = self.licitaciones.get(cl.get("licitacion_id"), {})
                cat_code = self.categories.get(r["category_id"])
                sub_code = self.subcategories.get(r["subcategory_id"], (None, None))[1]
                rows.append(
                    FakeRow(
                        id=r["id"],
                        classification_id=r["classification_id"],
                        reviewer_id=r["reviewer_id"],
                        reviewer_email=u["email"],
                        accepted=r["accepted"],
                        relevant=r.get("relevant"),
                        category_id=r["category_id"],
                        category_code=cat_code,
                        subcategory_id=r["subcategory_id"],
                        subcategory_code=sub_code,
                        relevance_tier=r.get("relevance_tier"),
                        reason=r.get("reason"),
                        created_at=r["created_at"],
                        licitacion_id=cl.get("licitacion_id"),
                        codigo=lic.get("codigo"),
                        nombre=lic.get("nombre"),
                    )
                )
            return FakeResult(rows)

        # 9. Review statistics
        if upper.startswith("SELECT COUNT(*) FROM KNOWLEDGE.HUMAN_REVIEWS WHERE ACCEPTED = TRUE"):
            count = sum(1 for r in self.human_reviews.values() if r["accepted"] is True)
            return FakeResult([FakeRow(count=count)])

        if upper.startswith("SELECT COUNT(*) FROM KNOWLEDGE.HUMAN_REVIEWS WHERE ACCEPTED = FALSE"):
            count = sum(1 for r in self.human_reviews.values() if r["accepted"] is False)
            return FakeResult([FakeRow(count=count)])

        if upper.startswith("SELECT COUNT(*) FROM KNOWLEDGE.HUMAN_REVIEWS"):
            return FakeResult([FakeRow(count=len(self.human_reviews))])

        if upper.startswith("SELECT COUNT(*) FROM KNOWLEDGE.CLASSIFICATIONS C"):
            reviewed_cl_ids = {r["classification_id"] for r in self.human_reviews.values()}
            unreviewed = sum(1 for cl_id in self.classifications if cl_id not in reviewed_cl_ids)
            return FakeResult([FakeRow(count=unreviewed)])

        # 10. Incorporate reviews query
        if "CL.TAXONOMY_VERSION" in upper:
            rows = []
            for r in self.human_reviews.values():
                u = self.users.get(r["reviewer_id"], {"email": "evaluator@test.cl"})
                cl = self.classifications.get(r["classification_id"], {})
                rows.append(
                    FakeRow(
                        id=r["id"],
                        classification_id=r["classification_id"],
                        reviewer_id=r["reviewer_id"],
                        reviewer_email=u["email"],
                        accepted=r["accepted"],
                        relevant=r.get("relevant", True),
                        category_id=r["category_id"],
                        subcategory_id=r["subcategory_id"],
                        reason=r.get("reason"),
                        created_at=r["created_at"],
                        licitacion_id=cl.get("licitacion_id"),
                        taxonomy_version=cl.get("taxonomy_version", "taxonomy-2026.2"),
                    )
                )
            return FakeResult(rows)

        # 11. Gold labels check / insert / update
        if upper.startswith("SELECT ID FROM KNOWLEDGE.GOLD_LABELS WHERE DATASET_VERSION_ID"):
            key = (params["dataset_version_id"], params["licitacion_id"])
            if key in self.gold_labels:
                return FakeResult([FakeRow(id=self.gold_labels[key]["id"])])
            return FakeResult([])

        if upper.startswith("INSERT INTO KNOWLEDGE.GOLD_LABELS"):
            key = (params["dataset_version_id"], params["licitacion_id"])
            self.gold_labels[key] = dict(params)
            return FakeResult([])

        if upper.startswith("UPDATE KNOWLEDGE.GOLD_LABELS SET"):
            for row in self.gold_labels.values():
                if row["id"] == params["id"]:
                    row.update(params)
                    break
            return FakeResult([])

        # 12. Ensure documents
        if upper.startswith("SELECT 1 FROM KNOWLEDGE.DOCUMENTS WHERE LICITACION_ID"):
            lic_id = params["licitacion_id"]
            if lic_id in self.documents:
                return FakeResult([FakeRow(val=1)])
            return FakeResult([])

        if upper.startswith("SELECT NOMBRE, DESCRIPCION FROM CORE.LICITACION WHERE ID"):
            lic_id = params["licitacion_id"]
            lic = self.licitaciones.get(lic_id)
            if lic:
                return FakeResult([FakeRow(nombre=lic["nombre"], descripcion=lic["descripcion"])])
            return FakeResult([])

        if upper.startswith("INSERT INTO KNOWLEDGE.DOCUMENTS"):
            self.documents[params["licitacion_id"]] = dict(params)
            return FakeResult([])

        # 13. Dataset versions count and manifest
        if upper.startswith("SELECT COUNT(*) FROM KNOWLEDGE.GOLD_LABELS WHERE DATASET_VERSION_ID"):
            count = sum(1 for row in self.gold_labels.values() if row["dataset_version_id"] == params["dataset_version_id"])
            return FakeResult([FakeRow(count=count)])

        if upper.startswith("SELECT MANIFEST FROM KNOWLEDGE.DATASET_VERSIONS WHERE ID"):
            ver = self.dataset_versions.get(params["id"])
            if ver:
                return FakeResult([FakeRow(manifest=ver["manifest"])])
            return FakeResult([])

        if upper.startswith("UPDATE KNOWLEDGE.DATASET_VERSIONS SET"):
            ver_id = params["id"]
            if ver_id in self.dataset_versions:
                self.dataset_versions[ver_id].update(params)
            return FakeResult([])

        return FakeResult([])


def test_fetch_review_queue_returns_both_low_conf_and_conflicting() -> None:
    db = FakeDB()
    queue = fetch_review_queue(db, only_unreviewed=True)

    assert len(queue) == 2
    # First item should be the one with higher priority (101 has high relevance + low conf)
    assert queue[0].licitacion_id == 101
    assert queue[0].priority > queue[1].priority
    assert "Silla de ruedas estándar" in queue[0].items


def test_record_human_review_accept_sets_confidence_to_one() -> None:
    db = FakeDB()
    cl_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    rev_user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    rev_id = record_human_review(
        db,
        classification_id=cl_id,
        reviewer_id=rev_user_id,
        accepted=True,
        relevant=True,
        category_id=1,
        subcategory_id=11,
        relevance_tier="high",
        reason="Predicción confirmada correctamente.",
    )

    assert rev_id in db.human_reviews
    assert db.human_reviews[rev_id]["accepted"] is True
    assert db.human_reviews[rev_id]["relevant"] is True

    # Classification confidence updated to 1.0
    assert db.classifications[cl_id]["confidence_score"] == 1.0
    assert db.classifications[cl_id]["explanation"]["human_review"]["accepted"] is True


def test_record_human_review_modify_updates_category_and_relevance() -> None:
    db = FakeDB()
    cl_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    rev_user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    rev_id = record_human_review(
        db,
        classification_id=cl_id,
        reviewer_id=rev_user_id,
        accepted=False,
        relevant=False,  # Modified to not relevant
        category_id=None,
        subcategory_id=None,
        relevance_tier="not_relevant",
        reason="Falso positivo: servicio de transporte municipal general, no para PcD.",
    )

    assert db.human_reviews[rev_id]["accepted"] is False
    assert db.human_reviews[rev_id]["relevant"] is False
    assert db.human_reviews[rev_id]["category_id"] is None

    # Classification reflects modified values
    assert db.classifications[cl_id]["category_id"] is None
    assert db.classifications[cl_id]["relevance_tier"] == "not_relevant"
    assert db.classifications[cl_id]["confidence_score"] == 1.0
    assert db.classifications[cl_id]["explanation"]["human_review"]["accepted"] is False


def test_get_review_statistics() -> None:
    db = FakeDB()
    cl_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    rev_user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    record_human_review(
        db,
        classification_id=cl_id,
        reviewer_id=rev_user_id,
        accepted=True,
        relevant=True,
        category_id=1,
        subcategory_id=11,
        relevance_tier="high",
        reason="Aceptado",
    )

    stats = get_review_statistics(db)
    assert stats["total_reviews"] == 1
    assert stats["accepted_count"] == 1
    assert stats["modified_count"] == 0
    assert stats["acceptance_rate"] == 1.0
    assert stats["unreviewed_classifications"] == 1


def test_incorporate_feedback_to_gold_dataset_syncs_labels() -> None:
    db = FakeDB()
    cl_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    rev_user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    dataset_version_id = uuid.UUID("99999999-9999-9999-9999-999999999999")

    record_human_review(
        db,
        classification_id=cl_id,
        reviewer_id=rev_user_id,
        accepted=True,
        relevant=True,
        category_id=1,
        subcategory_id=11,
        relevance_tier="high",
        reason="Suministro de ayudas técnicas confirmado.",
    )

    res = incorporate_feedback_to_gold_dataset(db, dataset_version_id=dataset_version_id)
    assert res["inserted"] == 1
    assert res["total_synced"] == 1
    assert res["record_count"] == 1

    # Check gold_labels has the record with reviewer identifier
    gold_key = (dataset_version_id, 101)
    assert gold_key in db.gold_labels
    label = db.gold_labels[gold_key]
    assert label["relevant"] is True
    assert label["category_id"] == 1
    assert label["subcategory_id"] == 11
    assert "human-review:evaluator@test.cl" in label["labeled_by"]
    assert "Suministro de ayudas técnicas" in label["notes"]

    # Manifest updated
    manifest = json.loads(db.dataset_versions[dataset_version_id]["manifest"])
    assert "human_review_feedback" in manifest
    assert manifest["human_review_feedback"]["synced_reviews_count"] == 1
