"""MLflow experiment tracking with graceful local fallback (Fase 6.23)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MLflowTracker:
    """Experiment tracker for MLflow.

    Provides a resilient interface that logs parameters, metrics, and artifacts to MLflow
    if available and configured, but falls back gracefully to structured in-memory and
    logging records when MLflow is unreachable or not installed.
    """

    def __init__(self, tracking_uri: str | None = None) -> None:
        self.tracking_uri = tracking_uri
        self._mlflow: Any = None
        self._active_run: Any = None
        self._in_memory_run: dict[str, Any] = {
            "experiment": None,
            "run_name": None,
            "params": {},
            "metrics": {},
            "artifacts": [],
            "status": "NOT_STARTED",
        }

        if tracking_uri:
            try:
                import mlflow

                mlflow.set_tracking_uri(tracking_uri)
                self._mlflow = mlflow
            except Exception as exc:
                logger.warning("Could not initialize MLflow client with URI '%s': %s", tracking_uri, exc)
                self._mlflow = None

    @property
    def is_connected(self) -> bool:
        return self._mlflow is not None and self._active_run is not None

    def start_run(self, experiment_name: str, run_name: str | None = None) -> str:
        self._in_memory_run["experiment"] = experiment_name
        self._in_memory_run["run_name"] = run_name
        self._in_memory_run["status"] = "RUNNING"

        if self._mlflow:
            try:
                self._mlflow.set_experiment(experiment_name)
                run = self._mlflow.start_run(run_name=run_name)
                self._active_run = run
                return run.info.run_id
            except Exception as exc:
                logger.warning("MLflow start_run failed, falling back to local tracking: %s", exc)
                self._active_run = None

        return f"local-run-{experiment_name}"

    def log_param(self, key: str, value: Any) -> None:
        self._in_memory_run["params"][key] = value
        if self._active_run and self._mlflow:
            try:
                self._mlflow.log_param(key, value)
            except Exception as exc:
                logger.debug("MLflow log_param failed: %s", exc)

    def log_params(self, params: dict[str, Any]) -> None:
        for k, v in params.items():
            self.log_param(k, v)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        self._in_memory_run["metrics"][key] = value
        if self._active_run and self._mlflow:
            try:
                self._mlflow.log_metric(key, value, step=step)
            except Exception as exc:
                logger.debug("MLflow log_metric failed: %s", exc)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                self.log_metric(k, float(v))

    def log_artifact(self, local_path: str, artifact_path: str | None = None) -> None:
        self._in_memory_run["artifacts"].append({
            "local_path": local_path,
            "artifact_path": artifact_path,
        })
        if self._active_run and self._mlflow:
            try:
                self._mlflow.log_artifact(local_path, artifact_path=artifact_path)
            except Exception as exc:
                logger.debug("MLflow log_artifact failed: %s", exc)

    def end_run(self, status: str = "FINISHED") -> None:
        self._in_memory_run["status"] = status
        if self._active_run and self._mlflow:
            try:
                self._mlflow.end_run(status=status)
            except Exception as exc:
                logger.debug("MLflow end_run failed: %s", exc)
        self._active_run = None

    def get_logged_data(self) -> dict[str, Any]:
        return dict(self._in_memory_run)
