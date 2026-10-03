import pytest

from app.nlp.taxonomy import (
    DomainConcept,
    Taxonomy,
    TaxonomyCategory,
    TaxonomySubcategory,
    load_initial_taxonomy,
    load_taxonomy,
)


def test_initial_taxonomy_is_valid_and_has_stable_hierarchy() -> None:
    taxonomy = load_initial_taxonomy()
    assert taxonomy.version == "taxonomy-2026.3"
    assert len(taxonomy.categories) == 7
    assert taxonomy.category("health").subcategories[0].code == "medical-equipment"
    assert all(category.subcategories for category in taxonomy.categories)


def test_frozen_version_2026_1_is_untouched() -> None:
    taxonomy = load_taxonomy("2026.1")
    assert taxonomy.version == "taxonomy-2026.1"
    subcategory_codes = {sub.code for cat in taxonomy.categories for sub in cat.subcategories}
    assert "geriatric-care" not in subcategory_codes
    assert not any(sub.concepts for cat in taxonomy.categories for sub in cat.subcategories)


def test_2026_2_adds_three_subcategories_with_nine_concepts() -> None:
    taxonomy = load_taxonomy("2026.2")
    health = taxonomy.category("health")
    construction = taxonomy.category("construction")

    subcategory_codes = {sub.code for sub in health.subcategories} | {sub.code for sub in construction.subcategories}
    assert {"geriatric-care", "assistive-technology", "accessibility-adaptation"} <= subcategory_codes

    all_concepts = [c for cat in taxonomy.categories for sub in cat.subcategories for c in sub.concepts]
    assert len(all_concepts) == 9


def test_2026_3_adds_an_apparel_category_unrelated_to_the_health_domain() -> None:
    """Shapewear (fajas reductoras/moldeadoras) is a separate business line from
    geriatría/discapacidad/accesibilidad (confirmed with the user) — it gets its
    own top-level category instead of a subcategory under `health`."""
    taxonomy = load_initial_taxonomy()
    apparel = taxonomy.category("apparel")

    assert len(apparel.subcategories) == 1
    shapewear = apparel.subcategories[0]
    assert shapewear.code == "shapewear"
    concept_codes = {c.code for c in shapewear.concepts}
    assert concept_codes == {"faja_reductora", "faja_moldeadora_short", "faja_moldeadora_colaless"}


def test_concept_lookup_finds_a_real_concept() -> None:
    taxonomy = load_initial_taxonomy()
    concept = taxonomy.concept("discapacidad")
    assert concept.name == "Discapacidad"


def test_taxonomy_rejects_unstable_or_duplicate_codes() -> None:
    taxonomy = Taxonomy(
        version="taxonomy-2026.1",
        categories=(
            TaxonomyCategory("Health", "Salud", "Descripción", (TaxonomySubcategory("care", "Atención", "Descripción"),)),
            TaxonomyCategory("Health", "Salud 2", "Descripción", (TaxonomySubcategory("care", "Atención", "Descripción"),)),
        ),
    )
    with pytest.raises(ValueError, match="duplicate category code"):
        taxonomy.validate()


def test_taxonomy_rejects_duplicate_concept_codes_across_subcategories() -> None:
    concept = DomainConcept("geriatria", "Geriatría", "Descripción")
    taxonomy = Taxonomy(
        version="taxonomy-2026.1",
        categories=(
            TaxonomyCategory("health", "Salud", "Descripción", (
                TaxonomySubcategory("sub-a", "A", "Descripción", concepts=(concept,)),
                TaxonomySubcategory("sub-b", "B", "Descripción", concepts=(concept,)),
            )),
        ),
    )
    with pytest.raises(ValueError, match="duplicate concept code"):
        taxonomy.validate()


def test_taxonomy_rejects_concept_without_name_or_description() -> None:
    taxonomy = Taxonomy(
        version="taxonomy-2026.1",
        categories=(
            TaxonomyCategory("health", "Salud", "Descripción", (
                TaxonomySubcategory("sub-a", "A", "Descripción", concepts=(DomainConcept("geriatria", "", "Descripción"),)),
            )),
        ),
    )
    with pytest.raises(ValueError, match="requires a name and description"):
        taxonomy.validate()
