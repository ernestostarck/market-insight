"""Pure, testable logic for the Gold Dataset (Fase 6.13): sampling, class
distribution, imbalance detection, stratified splitting, and label
consistency checks. Persistence lives in app/nlp/gold_dataset_db.py; the
interactive labeling loop lives in app/nlp/gold_dataset_cli.py.

The target domain (accesibilidad/ayudas técnicas/adultos mayores, per the
taxonomy/dictionary built in 6.5-6.9) is a tiny slice of all Mercado
Público tenders. A purely random sample would have ~0 positive examples
at a workable label-by-hand size, making "relevancia" a trivial, useless
label. `select_sample` stratifies: part of the sample is drawn from
licitaciones whose text already matched a known dictionary term
(candidate positives), the rest is uniform-random over the remaining
corpus (the real negative class) — representative of the classification
task, not of raw Mercado Público traffic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

_NOT_RELEVANT = "not_relevant"


def select_sample(
    all_ids: list[int],
    keyword_candidate_ids: list[int],
    *,
    target_size: int,
    keyword_share: float = 0.5,
    seed: int = 42,
) -> tuple[int, ...]:
    rng = random.Random(seed)
    keyword_target = round(target_size * keyword_share)
    keyword_pool = sorted(set(keyword_candidate_ids) & set(all_ids))
    keyword_pick = rng.sample(keyword_pool, min(keyword_target, len(keyword_pool)))

    remaining_pool = sorted(set(all_ids) - set(keyword_pool))
    remaining_target = target_size - len(keyword_pick)
    random_pick = rng.sample(remaining_pool, min(remaining_target, len(remaining_pool)))

    combined = keyword_pick + random_pick
    rng.shuffle(combined)
    return tuple(combined)


@dataclass(frozen=True, slots=True)
class ClassDistribution:
    counts: dict[str, int]
    total: int

    def share(self, code: str) -> float:
        return self.counts.get(code, 0) / self.total if self.total else 0.0


def compute_class_distribution(labels: list[dict]) -> ClassDistribution:
    """`labels` rows carry at least `relevant` and `category_code`
    (None when not relevant or not yet labeled — callers should filter
    to labeled rows first)."""
    counts: dict[str, int] = {}
    for row in labels:
        code = row["category_code"] if row.get("relevant") else _NOT_RELEVANT
        counts[code] = counts.get(code, 0) + 1
    return ClassDistribution(counts=counts, total=len(labels))


def detect_imbalance(distribution: ClassDistribution, *, min_share: float = 0.1) -> tuple[str, ...]:
    if distribution.total == 0:
        return ()
    return tuple(sorted(code for code in distribution.counts if distribution.share(code) < min_share))


def assign_splits(
    labeled_ids_by_category: dict[str, list[int]],
    *,
    train: float = 0.7,
    validation: float = 0.15,
    seed: int = 42,
) -> dict[int, str]:
    """Stratified by category so a rare category doesn't land 100% in one
    split. Each category's own ids are shuffled and cut independently."""
    if not (0 < train < 1) or not (0 <= validation < 1) or train + validation > 1:
        raise ValueError("train/validation shares must be fractions that leave room for test")

    rng = random.Random(seed)
    assignment: dict[int, str] = {}
    for ids in labeled_ids_by_category.values():
        ordered = sorted(ids)
        rng.shuffle(ordered)
        train_cut = round(len(ordered) * train)
        validation_cut = train_cut + round(len(ordered) * validation)
        for index, licitacion_id in enumerate(ordered):
            if index < train_cut:
                assignment[licitacion_id] = "train"
            elif index < validation_cut:
                assignment[licitacion_id] = "validation"
            else:
                assignment[licitacion_id] = "test"
    return assignment


def detect_inconsistencies(labels: list[dict]) -> tuple[str, ...]:
    """`labels` rows carry licitacion_id, relevant, category_id,
    subcategory_id, and (when subcategory_id is set) subcategory_category_id
    — the category_id that subcategory_id actually belongs to per the
    taxonomy, supplied by the caller's join (a DB lookup, not this pure
    function's concern)."""
    issues: list[str] = []
    for row in labels:
        licitacion_id = row["licitacion_id"]
        if row.get("relevant") and row.get("category_id") is None:
            issues.append(f"licitacion_id={licitacion_id}: relevant=True sin category_id")
        if row.get("relevant") is False and row.get("category_id") is not None:
            issues.append(f"licitacion_id={licitacion_id}: relevant=False pero tiene category_id")
        subcategory_id = row.get("subcategory_id")
        subcategory_category_id = row.get("subcategory_category_id")
        if subcategory_id is not None and subcategory_category_id != row.get("category_id"):
            issues.append(f"licitacion_id={licitacion_id}: subcategory_id no pertenece a category_id")
    return tuple(issues)
