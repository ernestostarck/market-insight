from app.nlp.product_attributes import extract_product_attributes


def test_extracts_material() -> None:
    attributes = extract_product_attributes("silla de ruedas fabricada en acero inoxidable")

    assert attributes.materiales == ("acero inoxidable",)


def test_material_word_boundary_does_not_match_inside_another_word() -> None:
    """Regression: same class of bug as marca/modelo in 6.11 — a plain
    substring 'manual' would wrongly match inside 'manualidades'."""
    attributes = extract_product_attributes("taller de manualidades para adultos mayores")

    assert "manual" not in attributes.caracteristicas_tecnicas


def test_no_material_without_a_known_keyword() -> None:
    attributes = extract_product_attributes("silla de ruedas estandar")

    assert attributes.materiales == ()


def test_extracts_3d_dimensiones() -> None:
    attributes = extract_product_attributes("camilla de 60 cm x 40 cm x 90 cm")

    assert attributes.dimensiones == "60 cm x 40 cm x 90 cm"


def test_extracts_1d_dimension() -> None:
    attributes = extract_product_attributes("rampa de 80 cm de ancho")

    assert attributes.dimensiones == "80 cm de ancho"


def test_no_dimensiones_without_a_pattern() -> None:
    attributes = extract_product_attributes("silla de ruedas estandar")

    assert attributes.dimensiones is None


def test_extracts_capacidad_with_capacidad_keyword() -> None:
    attributes = extract_product_attributes("grua de traslado con capacidad de carga de 120 kg")

    assert attributes.capacidad == "120 kg"


def test_extracts_capacidad_with_hasta() -> None:
    attributes = extract_product_attributes("silla de ruedas para pacientes de hasta 150 kg")

    assert attributes.capacidad == "150 kg"


def test_no_capacidad_without_a_pattern() -> None:
    attributes = extract_product_attributes("silla de ruedas estandar")

    assert attributes.capacidad is None


def test_extracts_caracteristicas_tecnicas() -> None:
    attributes = extract_product_attributes("silla de ruedas plegable, regulable en altura, con freno")

    assert set(attributes.caracteristicas_tecnicas) == {"plegable", "regulable en altura", "con freno"}


def test_no_caracteristicas_without_known_keywords() -> None:
    attributes = extract_product_attributes("silla de ruedas estandar")

    assert attributes.caracteristicas_tecnicas == ()
