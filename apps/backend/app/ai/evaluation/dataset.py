"""Evaluation Dataset schemas and loader (Fase 9.22).

Defines canonical gold standard benchmarks across 8 distinct query categories:
1. quantitative (Gasto, montos, agregaciones numéricas)
2. semantic (Búsqueda conceptual, descripciones técnicas)
3. hybrid (Palabras clave + filtros relacionales)
4. contextual (Turnos dependientes de historial y memoria)
5. no_evidence (Consultas sobre datos inexistentes; exige respuesta honesta)
6. ambiguous (Consultas con múltiples entidades sin resolver; exige clarificación)
7. adversarial (Preguntas fuera de dominio como recetas, poesía, código)
8. prompt_injection (Intentos de evasión de instrucciones y jailbreaks)
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvaluationCategory(StrEnum):
    QUANTITATIVE = "quantitative"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    CONTEXTUAL = "contextual"
    NO_EVIDENCE = "no_evidence"
    AMBIGUOUS = "ambiguous"
    ADVERSARIAL = "adversarial"
    PROMPT_INJECTION = "prompt_injection"


class DifficultyLevel(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationTestCase(BaseModel):
    """Individual gold standard evaluation instance."""

    id: str = Field(..., description="Unique benchmark case identifier.")
    question: str = Field(..., description="User query prompt.")
    expected_answer: str = Field(..., description="Canonical reference answer or guideline.")
    expected_sources: list[str] = Field(default_factory=list, description="IDs of ground truth relevant sources.")
    expected_retrieval: str = Field(..., description="Expected retrieval strategy (DIRECT, SQL, VECTOR, HYBRID).")
    category: EvaluationCategory = Field(..., description="Query evaluation category.")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="Task difficulty.")
    gold_answers: list[str] = Field(default_factory=list, description="Key accepted factual phrases or answers.")
    gold_sources: list[str] = Field(default_factory=list, description="Ground truth source IDs.")
    gold_retrieval: str = Field(..., description="Ground truth retrieval strategy.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationDataset(BaseModel):
    """Collection of benchmark test cases."""

    name: str = "mercado_insight_rag_gold_benchmark"
    version: str = "1.0.0"
    description: str = "Canonical evaluation dataset covering retrieval, generation and system guardrails."
    test_cases: list[EvaluationTestCase] = Field(default_factory=list)

    def filter_by_category(self, category: EvaluationCategory) -> list[EvaluationTestCase]:
        """Return test cases belonging to a specific evaluation category."""
        return [tc for tc in self.test_cases if tc.category == category]

    @classmethod
    def load_canonical(cls, dataset_path: Path | None = None) -> EvaluationDataset:
        """Load the standard canonical gold dataset from disk."""
        if dataset_path is None:
            dataset_path = Path(__file__).parent / "data" / "gold_evaluation_dataset.json"

        if not dataset_path.exists():
            raise FileNotFoundError(f"Canonical benchmark dataset not found at {dataset_path}")

        with open(dataset_path, encoding="utf-8") as f:
            raw_data = json.load(f)

        return cls.model_validate(raw_data)
