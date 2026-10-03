import pytest

from app.nlp.dictionary import (
    DictionaryEntry,
    DomainDictionary,
    DomainTheme,
    load_initial_dictionary,
)
from app.nlp.taxonomy import load_initial_taxonomy


def test_initial_dictionary_loads_and_is_valid() -> None:
    dictionary = load_initial_dictionary()
    assert dictionary.version == "dictionary-2026.1"
    assert dictionary.entries


def test_every_domain_theme_has_at_least_one_entry() -> None:
    dictionary = load_initial_dictionary()
    covered = {entry.theme for entry in dictionary.entries}
    assert covered == set(DomainTheme)


def test_domain_themes_match_taxonomy_concepts_exactly() -> None:
    """The 9 DomainTheme values (6.4) must be exactly the 9 Concept codes the
    geriatric/disability dictionary bridges into the taxonomy (6.5) — that
    identity IS the formal bridge for THIS domain, not an indirect mapping
    table. `taxonomy-2026.3` also carries the unrelated `apparel` category
    (shapewear, a separate business line — confirmed with the user), which
    intentionally has no DomainTheme and sits outside this bridge."""
    taxonomy = load_initial_taxonomy()
    concept_codes = {
        concept.code
        for category in taxonomy.categories
        for subcategory in category.subcategories
        for concept in subcategory.concepts
    }
    theme_values = {theme.value for theme in DomainTheme}
    assert theme_values <= concept_codes
    assert concept_codes - theme_values == {
        "faja_reductora", "faja_moldeadora_short", "faja_moldeadora_colaless",
    }


def test_category_codes_used_in_the_real_dictionary_exist_in_the_real_taxonomy() -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()

    with_category = [entry for entry in dictionary.entries if entry.category_code]
    assert with_category  # sanity: the fixture actually exercises this path

    for entry in with_category:
        category = taxonomy.category(entry.category_code)
        if entry.subcategory_code:
            assert any(sub.code == entry.subcategory_code for sub in category.subcategories)


def test_validate_rejects_version_without_dictionary_prefix() -> None:
    dictionary = DomainDictionary(
        version="2026.1",
        entries=tuple(
            DictionaryEntry(concept=theme.value, theme=theme, term=theme.value) for theme in DomainTheme
        ),
    )
    with pytest.raises(ValueError):
        dictionary.validate()


def test_validate_rejects_missing_theme_coverage() -> None:
    dictionary = DomainDictionary(
        version="dictionary-test",
        entries=(DictionaryEntry(concept="geriatria", theme=DomainTheme.GERIATRIA, term="geriatria"),),
    )
    with pytest.raises(ValueError, match="missing entries for theme"):
        dictionary.validate()


def _full_coverage_entries() -> tuple[DictionaryEntry, ...]:
    return tuple(
        DictionaryEntry(concept=f"concept_{theme.value}", theme=theme, term=f"term {theme.value}")
        for theme in DomainTheme
    )


def test_validate_rejects_duplicate_concept() -> None:
    entries = _full_coverage_entries()
    duplicate = entries + (DictionaryEntry(concept=entries[0].concept, theme=DomainTheme.GERIATRIA, term="otro"),)
    dictionary = DomainDictionary(version="dictionary-test", entries=duplicate)
    with pytest.raises(ValueError, match="duplicate concept"):
        dictionary.validate()


def test_validate_rejects_duplicate_surface_form_across_entries() -> None:
    entries = list(_full_coverage_entries())
    entries[1] = DictionaryEntry(
        concept="another_concept", theme=DomainTheme.ADULTOS_MAYORES, term="shared term",
        synonyms=(entries[0].term,),
    )
    dictionary = DomainDictionary(version="dictionary-test", entries=tuple(entries))
    with pytest.raises(ValueError, match="duplicate surface form"):
        dictionary.validate()


def test_validate_rejects_subcategory_without_category() -> None:
    entries = list(_full_coverage_entries())
    entries[0] = DictionaryEntry(
        concept=entries[0].concept, theme=entries[0].theme, term=entries[0].term,
        subcategory_code="medical-equipment",
    )
    dictionary = DomainDictionary(version="dictionary-test", entries=tuple(entries))
    with pytest.raises(ValueError, match="subcategory_code without category_code"):
        dictionary.validate()


def test_validate_rejects_unknown_category_against_real_taxonomy() -> None:
    entries = list(_full_coverage_entries())
    entries[0] = DictionaryEntry(
        concept=entries[0].concept, theme=entries[0].theme, term=entries[0].term,
        category_code="not-a-real-category",
    )
    dictionary = DomainDictionary(version="dictionary-test", entries=tuple(entries))
    with pytest.raises(ValueError, match="unknown category_code"):
        dictionary.validate(load_initial_taxonomy())


def test_validate_rejects_unknown_subcategory_against_real_taxonomy() -> None:
    entries = list(_full_coverage_entries())
    entries[0] = DictionaryEntry(
        concept=entries[0].concept, theme=entries[0].theme, term=entries[0].term,
        category_code="health", subcategory_code="not-a-real-subcategory",
    )
    dictionary = DomainDictionary(version="dictionary-test", entries=tuple(entries))
    with pytest.raises(ValueError, match="unknown subcategory_code"):
        dictionary.validate(load_initial_taxonomy())


def test_all_surface_forms_combines_term_synonyms_and_abbreviations() -> None:
    entry = DictionaryEntry(
        concept="silla_de_ruedas", theme=DomainTheme.MOVILIDAD_REDUCIDA, term="silla de ruedas",
        synonyms=("silla de ruedas manual",), abbreviations=("s/r",),
    )
    assert entry.all_surface_forms() == ("silla de ruedas", "silla de ruedas manual", "s/r")
