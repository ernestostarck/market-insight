from app.nlp.contracts import ArtifactVersions, NLPJobRequest
from app.services.nlp import NLPService


class Dispatcher:
    def __init__(self) -> None:
        self.job: NLPJobRequest | None = None

    def dispatch(self, job: NLPJobRequest) -> str:
        self.job = job
        return "task-123"


def test_service_dispatches_versioned_job_to_worker() -> None:
    dispatcher = Dispatcher()
    service = NLPService(None, None, dispatcher)  # type: ignore[arg-type]
    job = NLPJobRequest(7, "a" * 64, ArtifactVersions("taxonomy-1", "dictionary-1"))
    assert service.submit(job) == "task-123"
    assert dispatcher.job == job


def test_job_payload_round_trip_preserves_idempotency_key() -> None:
    job = NLPJobRequest(7, "a" * 64, ArtifactVersions("taxonomy-1", "dictionary-1", "model-1", "embed-1"))
    assert NLPJobRequest.from_payload(job.to_payload()).idempotency_key == job.idempotency_key
