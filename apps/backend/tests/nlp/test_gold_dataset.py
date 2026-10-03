from app.nlp.gold_dataset import (
    assign_splits, compute_class_distribution, detect_imbalance, detect_inconsistencies, select_sample,
)


def test_select_sample_respects_keyword_share() -> None:
    all_ids = list(range(1, 101))
    keyword_ids = list(range(1, 21))  # 20 keyword candidates

    sample = select_sample(all_ids, keyword_ids, target_size=10, keyword_share=0.5, seed=1)

    assert len(sample) == 10
    keyword_hits = [i for i in sample if i in keyword_ids]
    assert len(keyword_hits) == 5


def test_select_sample_is_deterministic_for_the_same_seed() -> None:
    all_ids = list(range(1, 101))
    keyword_ids = list(range(1, 21))

    first = select_sample(all_ids, keyword_ids, target_size=10, seed=7)
    second = select_sample(all_ids, keyword_ids, target_size=10, seed=7)

    assert first == second


def test_select_sample_does_not_exceed_available_pool() -> None:
    all_ids = [1, 2, 3]
    keyword_ids = [1]

    sample = select_sample(all_ids, keyword_ids, target_size=10, seed=1)

    assert set(sample) == {1, 2, 3}
    assert len(sample) == 3


def test_select_sample_has_no_duplicates() -> None:
    all_ids = list(range(1, 51))
    keyword_ids = list(range(1, 11))

    sample = select_sample(all_ids, keyword_ids, target_size=20, seed=3)

    assert len(sample) == len(set(sample))


def test_compute_class_distribution_groups_relevant_by_category() -> None:
    labels = [
        {"relevant": True, "category_code": "health"},
        {"relevant": True, "category_code": "health"},
        {"relevant": True, "category_code": "construction"},
        {"relevant": False, "category_code": None},
    ]

    distribution = compute_class_distribution(labels)

    assert distribution.total == 4
    assert distribution.counts == {"health": 2, "construction": 1, "not_relevant": 1}
    assert distribution.share("health") == 0.5


def test_detect_imbalance_flags_classes_below_threshold() -> None:
    labels = [{"relevant": True, "category_code": "health"}] * 9 + [
        {"relevant": True, "category_code": "construction"}
    ]

    distribution = compute_class_distribution(labels)
    imbalanced = detect_imbalance(distribution, min_share=0.15)

    assert imbalanced == ("construction",)


def test_detect_imbalance_empty_distribution_returns_nothing() -> None:
    assert detect_imbalance(compute_class_distribution([])) == ()


def test_assign_splits_is_stratified_per_category() -> None:
    grouped = {"health": list(range(1, 11)), "not_relevant": list(range(11, 21))}

    assignment = assign_splits(grouped, train=0.7, validation=0.15, seed=1)

    health_splits = {assignment[i] for i in range(1, 11)}
    assert health_splits <= {"train", "validation", "test"}
    train_count = sum(1 for i in range(1, 11) if assignment[i] == "train")
    assert train_count == 7


def test_assign_splits_is_deterministic_for_the_same_seed() -> None:
    grouped = {"health": list(range(1, 11))}

    first = assign_splits(grouped, seed=5)
    second = assign_splits(grouped, seed=5)

    assert first == second


def test_assign_splits_rejects_invalid_shares() -> None:
    try:
        assign_splits({"health": [1]}, train=0.9, validation=0.5)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_detect_inconsistencies_flags_relevant_without_category() -> None:
    labels = [{"licitacion_id": 1, "relevant": True, "category_id": None, "subcategory_id": None}]

    issues = detect_inconsistencies(labels)

    assert len(issues) == 1
    assert "licitacion_id=1" in issues[0]


def test_detect_inconsistencies_flags_not_relevant_with_category() -> None:
    labels = [{"licitacion_id": 2, "relevant": False, "category_id": 3, "subcategory_id": None}]

    issues = detect_inconsistencies(labels)

    assert len(issues) == 1
    assert "licitacion_id=2" in issues[0]


def test_detect_inconsistencies_flags_subcategory_mismatch() -> None:
    labels = [{
        "licitacion_id": 3, "relevant": True, "category_id": 1,
        "subcategory_id": 5, "subcategory_category_id": 2,
    }]

    issues = detect_inconsistencies(labels)

    assert len(issues) == 1
    assert "licitacion_id=3" in issues[0]


def test_detect_inconsistencies_clean_labels_produce_no_issues() -> None:
    labels = [
        {"licitacion_id": 1, "relevant": True, "category_id": 1, "subcategory_id": 5, "subcategory_category_id": 1},
        {"licitacion_id": 2, "relevant": False, "category_id": None, "subcategory_id": None},
    ]

    assert detect_inconsistencies(labels) == ()
