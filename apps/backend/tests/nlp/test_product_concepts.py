from app.nlp.dictionary import load_initial_dictionary
from app.nlp.product_concepts import match_product_concepts, product_concept_entries

_DICTIONARY = load_initial_dictionary()


def test_product_concept_entries_are_exactly_the_category_coded_ones() -> None:
    entries = product_concept_entries(_DICTIONARY)

    assert len(entries) == 16
    assert all(entry.category_code is not None for entry in entries)
    codes = {entry.concept for entry in entries}
    assert "silla_de_ruedas" in codes
    assert "geriatria" not in codes  # cross-cutting topic, no category_code


def test_matches_the_term() -> None:
    matches = match_product_concepts("Se requiere silla de ruedas para paciente", _DICTIONARY)

    assert len(matches) == 1
    assert matches[0].concept_code == "silla_de_ruedas"
    assert matches[0].category_code == "health"
    assert matches[0].subcategory_code == "medical-equipment"
    assert matches[0].matched_term == "silla de ruedas"


def test_matches_a_synonym() -> None:
    matches = match_product_concepts("silla de ruedas electrica plegable", _DICTIONARY)

    assert any(match.concept_code == "silla_de_ruedas" for match in matches)


def test_no_match_for_text_without_a_known_product() -> None:
    matches = match_product_concepts("servicio de aseo general de oficinas", _DICTIONARY)

    assert matches == ()


def test_item_mentioning_two_products_gives_two_matches() -> None:
    matches = match_product_concepts("silla de ruedas y rampa de acceso para el mismo recinto", _DICTIONARY)

    codes = {match.concept_code for match in matches}
    assert codes == {"silla_de_ruedas", "rampa_de_acceso"}


def test_offsets_point_at_the_matched_term() -> None:
    text_value = "requiere andador ortopedico"
    matches = match_product_concepts(text_value, _DICTIONARY)

    andador_match = next(match for match in matches if match.concept_code == "andador")
    assert text_value[andador_match.start_offset:andador_match.end_offset].casefold() == andador_match.matched_term.casefold()
