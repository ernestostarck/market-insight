from app.nlp.dictionary import load_initial_dictionary
from app.nlp.rules import Rule, RuleEngine, build_ruleset
from app.nlp.taxonomy import load_initial_taxonomy


def _rule(**overrides) -> Rule:
    defaults = dict(
        id="r1", concept_code="geriatria", category_code="health",
        subcategory_code="geriatric-care", keyword="geriatria",
    )
    defaults.update(overrides)
    return Rule(**defaults)


def test_evaluate_matches_keyword_case_insensitively() -> None:
    engine = RuleEngine([_rule(keyword="silla de ruedas")])

    evaluation = engine.evaluate("Se requiere una SILLA DE RUEDAS plegable")

    assert evaluation.category_code == "health"
    assert evaluation.subcategory_code == "geriatric-care"
    assert evaluation.score == 1.0
    assert evaluation.matches[0].concept_code == "geriatria"


def test_evaluate_ignores_inactive_rules() -> None:
    engine = RuleEngine([_rule(active=False)])

    evaluation = engine.evaluate("geriatria")

    assert evaluation.score == 0.0
    assert evaluation.matches == ()


def test_evaluate_supports_regex_rules() -> None:
    engine = RuleEngine([_rule(keyword=r"silla(s)? de ruedas", is_regex=True)])

    evaluation = engine.evaluate("Se compran sillas de ruedas plegables")

    assert evaluation.score == 1.0
    assert evaluation.matches[0].keyword == r"silla(s)? de ruedas"


def test_evaluate_regex_rule_does_not_match_without_pattern() -> None:
    engine = RuleEngine([_rule(keyword=r"silla(s)? de ruedas", is_regex=True)])

    evaluation = engine.evaluate("no hay coincidencia aqui")

    assert evaluation.score == 0.0


def test_evaluate_picks_highest_scoring_category_subcategory_pair() -> None:
    engine = RuleEngine([
        _rule(id="r1", category_code="health", subcategory_code="geriatric-care", keyword="geriatria", weight=1.0),
        _rule(id="r2", category_code="construction", subcategory_code="accessibility-adaptation", keyword="rampa", weight=2.0),
    ])

    evaluation = engine.evaluate("licitacion de geriatria y tambien rampa de acceso")

    assert evaluation.category_code == "construction"
    assert evaluation.score == 2.0
    assert len(evaluation.matches) == 2


def test_evaluate_empty_ruleset_returns_no_match() -> None:
    evaluation = RuleEngine([]).evaluate("cualquier texto")

    assert evaluation.category_code is None
    assert evaluation.score == 0.0
    assert evaluation.matches == ()


def test_build_ruleset_covers_every_dictionary_entry_surface_form() -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()

    rules = build_ruleset(dictionary, taxonomy)

    expected_count = sum(len(entry.all_surface_forms()) for entry in dictionary.entries)
    assert len(rules) == expected_count
    assert all(rule.version == dictionary.version for rule in rules)
    assert all(rule.active for rule in rules)


def test_build_ruleset_marks_abbreviations_as_word_boundary_regex() -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()
    entry_with_abbreviation = next(e for e in dictionary.entries if e.abbreviations)

    rules = build_ruleset(dictionary, taxonomy)

    abbreviation_rules = [
        r for r in rules
        if r.id.startswith(f"{dictionary.version}:{entry_with_abbreviation.concept}:")
        and r.weight == entry_with_abbreviation.weight
        and any(abbr in r.keyword for abbr in entry_with_abbreviation.abbreviations)
    ]
    assert abbreviation_rules
    assert all(rule.is_regex for rule in abbreviation_rules)
    assert all(rule.keyword.startswith(r"\b") and rule.keyword.endswith(r"\b") for rule in abbreviation_rules)


def test_short_abbreviation_rule_does_not_match_inside_unrelated_words() -> None:
    """Regression: 'to' (terapia ocupacional) matched inside 'servicio',
    'auditorio', etc. with plain substring search against real ChileCompra
    text. Confirms the word-boundary regex fix."""
    rule = Rule(
        id="r1", concept_code="rehabilitacion", category_code="health", keyword=r"\bto\b",
        is_regex=True,
    )
    engine = RuleEngine([rule])

    evaluation = engine.evaluate("servicio de apoyo audiovisual para el auditorio")

    assert evaluation.score == 0.0


def test_build_ruleset_resolves_concept_code_from_theme() -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()

    rules = build_ruleset(dictionary, taxonomy)

    entries_by_concept = {entry.concept: entry for entry in dictionary.entries}
    for rule in rules:
        entry = next(e for e in dictionary.entries if rule.id.split(":")[1] == e.concept)
        assert rule.concept_code == entry.theme.value
        assert entries_by_concept[entry.concept] is entry


def test_build_ruleset_uses_explicit_category_when_entry_has_one() -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()
    entry_with_category = next(e for e in dictionary.entries if e.category_code)

    rules = build_ruleset(dictionary, taxonomy)

    matching_rules = [r for r in rules if r.id.startswith(f"{dictionary.version}:{entry_with_category.concept}:")]
    assert matching_rules
    assert all(r.category_code == entry_with_category.category_code for r in matching_rules)


def test_build_ruleset_derives_category_from_concept_when_entry_has_none() -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()
    entry_without_category = next(e for e in dictionary.entries if not e.category_code)

    rules = build_ruleset(dictionary, taxonomy)

    matching_rules = [r for r in rules if r.id.startswith(f"{dictionary.version}:{entry_without_category.concept}:")]
    category, subcategory, _ = taxonomy.locate(entry_without_category.theme.value)
    assert matching_rules
    assert all(r.category_code == category.code for r in matching_rules)
    assert all(r.subcategory_code == subcategory.code for r in matching_rules)


def test_taxonomy_locate_raises_for_unknown_concept() -> None:
    taxonomy = load_initial_taxonomy()
    try:
        taxonomy.locate("no-such-concept")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")

