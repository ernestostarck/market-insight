import uuid

from app.nlp.classifier_training_db import (
    latest_production_or_staging_classifier, register_model_version, set_artifact_uri,
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


class FakeConnection:
    def __init__(self) -> None:
        self.model_versions: dict[uuid.UUID, dict] = {}

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        upper = sql.upper()
        params = params or {}

        if upper.startswith("SELECT ID FROM KNOWLEDGE.MODEL_VERSIONS WHERE NAME"):
            for model_version_id, row in self.model_versions.items():
                if row["name"] == params["name"] and row["version"] == params["version"]:
                    return FakeResult([FakeRow(id=model_version_id)])
            return FakeResult([])

        if upper.startswith("UPDATE KNOWLEDGE.MODEL_VERSIONS SET STATUS"):
            self.model_versions[params["id"]].update({
                "status": params["status"], "parameters": params["parameters"], "metrics": params["metrics"],
            })
            return FakeResult([])

        if upper.startswith("INSERT INTO KNOWLEDGE.MODEL_VERSIONS"):
            self.model_versions[params["id"]] = dict(params)
            return FakeResult([])

        if upper.startswith("SELECT ID, NAME, VERSION, ARTIFACT_URI, PARAMETERS"):
            candidates = [
                (mvid, row) for mvid, row in self.model_versions.items()
                if row.get("kind", "classifier") == "classifier" and row.get("status") == params["status"]
            ]
            if not candidates:
                return FakeResult([])
            model_version_id, row = candidates[-1]
            return FakeResult([FakeRow(
                id=model_version_id, name=row["name"], version=row["version"],
                artifact_uri=row.get("artifact_uri"), parameters=row.get("parameters"),
            )])

        if upper.startswith("UPDATE KNOWLEDGE.MODEL_VERSIONS SET ARTIFACT_URI"):
            self.model_versions[params["id"]]["artifact_uri"] = params["artifact_uri"]
            return FakeResult([])

        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self) -> None:
        pass


def test_register_model_version_creates_new() -> None:
    connection = FakeConnection()

    model_version_id = register_model_version(
        connection, name="tfidf_logreg", version="v1", status="staging",
        parameters={"dataset_version_id": "abc"}, metrics={"f1_macro": 0.8},
    )

    assert connection.model_versions[model_version_id]["status"] == "staging"


def test_register_model_version_updates_existing_on_reregister() -> None:
    connection = FakeConnection()
    first_id = register_model_version(
        connection, name="tfidf_logreg", version="v1", status="staging", parameters={}, metrics={"f1_macro": 0.5},
    )

    second_id = register_model_version(
        connection, name="tfidf_logreg", version="v1", status="production", parameters={}, metrics={"f1_macro": 0.9},
    )

    assert first_id == second_id
    assert connection.model_versions[first_id]["status"] == "production"


def test_latest_production_or_staging_classifier_prefers_production() -> None:
    connection = FakeConnection()
    register_model_version(connection, name="a", version="v1", status="staging", parameters={}, metrics={})
    register_model_version(connection, name="b", version="v1", status="production", parameters={}, metrics={})

    result = latest_production_or_staging_classifier(connection)

    assert result["name"] == "b"


def test_latest_production_or_staging_classifier_falls_back_to_staging() -> None:
    connection = FakeConnection()
    register_model_version(connection, name="a", version="v1", status="staging", parameters={}, metrics={})

    result = latest_production_or_staging_classifier(connection)

    assert result["name"] == "a"


def test_latest_production_or_staging_classifier_returns_none_when_none_trained() -> None:
    connection = FakeConnection()

    assert latest_production_or_staging_classifier(connection) is None


def test_set_artifact_uri() -> None:
    connection = FakeConnection()
    model_version_id = register_model_version(
        connection, name="a", version="v1", status="staging", parameters={}, metrics={},
    )

    set_artifact_uri(connection, model_version_id, "s3://ml-models/a-v1.joblib")

    assert connection.model_versions[model_version_id]["artifact_uri"] == "s3://ml-models/a-v1.joblib"
