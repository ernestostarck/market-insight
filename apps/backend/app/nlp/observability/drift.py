"""Data distribution drift detection for NLP classification (Fase 6.24)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.nlp.observability.metrics import NLP_DATA_DRIFT_KL_DIVERGENCE

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DriftReport:
    """Evaluation of distributional shift between current traffic and Gold Dataset baseline."""

    kl_divergence: float
    drift_detected: bool
    threshold: float
    observed_distribution: dict[str, float]
    baseline_distribution: dict[str, float]
    largest_shift_category: str | None


class DataDriftDetector:
    """Monitors shifting label/category distributions using Kullback-Leibler (KL) divergence."""

    def __init__(self, drift_threshold: float = 0.20, smoothing_eps: float = 1e-5) -> None:
        self.drift_threshold = drift_threshold
        self.smoothing_eps = smoothing_eps

    def compute_drift(
        self,
        observed_counts: dict[str, int | float],
        baseline_counts: dict[str, int | float],
    ) -> DriftReport:
        """Calculate KL divergence D_KL(P || Q) from baseline Q to observed P."""
        all_categories = sorted(set(observed_counts.keys()) | set(baseline_counts.keys()))
        if not all_categories:
            return DriftReport(
                kl_divergence=0.0,
                drift_detected=False,
                threshold=self.drift_threshold,
                observed_distribution={},
                baseline_distribution={},
                largest_shift_category=None,
            )

        total_obs = sum(observed_counts.values()) or 1.0
        total_base = sum(baseline_counts.values()) or 1.0

        p_dist: dict[str, float] = {}
        q_dist: dict[str, float] = {}

        for cat in all_categories:
            p_dist[cat] = (observed_counts.get(cat, 0.0) + self.smoothing_eps) / (
                total_obs + self.smoothing_eps * len(all_categories)
            )
            q_dist[cat] = (baseline_counts.get(cat, 0.0) + self.smoothing_eps) / (
                total_base + self.smoothing_eps * len(all_categories)
            )

        kl_div = 0.0
        largest_shift_cat: str | None = None
        max_shift = -1.0

        for cat in all_categories:
            p = p_dist[cat]
            q = q_dist[cat]
            divergence_term = p * math.log(p / q)
            kl_div += divergence_term

            abs_diff = abs(p - q)
            if abs_diff > max_shift:
                max_shift = abs_diff
                largest_shift_cat = cat

        kl_div = round(max(0.0, kl_div), 6)
        drift_detected = kl_div > self.drift_threshold

        # Update Prometheus gauge
        try:
            NLP_DATA_DRIFT_KL_DIVERGENCE.set(kl_div)
        except (TypeError, ValueError) as err:
            logger.debug("Could not record drift metric: %s", err)

        return DriftReport(
            kl_divergence=kl_div,
            drift_detected=drift_detected,
            threshold=self.drift_threshold,
            observed_distribution={k: round(v, 4) for k, v in p_dist.items()},
            baseline_distribution={k: round(v, 4) for k, v in q_dist.items()},
            largest_shift_category=largest_shift_cat,
        )
