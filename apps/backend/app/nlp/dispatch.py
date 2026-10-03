"""API-to-worker boundary for NLP jobs."""

from __future__ import annotations

from typing import Protocol

from app.nlp.contracts import NLPJobRequest


class NLPJobDispatcher(Protocol):
    def dispatch(self, job: NLPJobRequest) -> str: ...


class CeleryNLPJobDispatcher:
    def dispatch(self, job: NLPJobRequest) -> str:
        from app.worker.nlp_tasks import process_nlp_job

        return str(process_nlp_job.apply_async(args=[job.to_payload()], queue="nlp").id)
