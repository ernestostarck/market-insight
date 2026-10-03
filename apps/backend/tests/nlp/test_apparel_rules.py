from app.nlp.apparel_rules import build_apparel_ruleset
from app.nlp.rules import RuleEngine


def test_build_apparel_ruleset_covers_every_concept_with_a_stable_id() -> None:
    rules = build_apparel_ruleset()

    concept_codes = {rule.concept_code for rule in rules}
    assert concept_codes == {"faja_reductora", "faja_moldeadora_short", "faja_moldeadora_colaless"}
    assert all(rule.category_code == "apparel" for rule in rules)
    assert all(rule.subcategory_code == "shapewear" for rule in rules)
    assert len({rule.id for rule in rules}) == len(rules)  # every id is unique


def test_faja_moldeadora_tipo_short_sin_costuras_matches() -> None:
    engine = RuleEngine(build_apparel_ruleset())

    evaluation = engine.evaluate("Compra de faja body moldeadora tipo short sin costuras")

    assert evaluation.category_code == "apparel"
    assert evaluation.subcategory_code == "shapewear"
    assert any(m.concept_code == "faja_moldeadora_short" for m in evaluation.matches)


def test_faja_moldeadora_tipo_colaless_con_cierre_frontal_matches() -> None:
    engine = RuleEngine(build_apparel_ruleset())

    evaluation = engine.evaluate("Faja body moldeadora tipo colaless (tanga) con cierre frontal")

    assert evaluation.category_code == "apparel"
    assert any(m.concept_code == "faja_moldeadora_colaless" for m in evaluation.matches)


def test_generic_faja_reductora_mention_still_matches() -> None:
    engine = RuleEngine(build_apparel_ruleset())

    evaluation = engine.evaluate("Adquisición de fajas reductoras para dotación")

    assert evaluation.category_code == "apparel"
    assert any(m.concept_code == "faja_reductora" for m in evaluation.matches)


def test_unrelated_geriatric_text_does_not_match_apparel_rules() -> None:
    engine = RuleEngine(build_apparel_ruleset())

    evaluation = engine.evaluate("Compra de sillas de ruedas para adultos mayores")

    assert evaluation.score == 0.0
    assert evaluation.matches == ()
