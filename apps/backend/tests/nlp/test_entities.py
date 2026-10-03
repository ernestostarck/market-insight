from app.nlp.entities import extract_text_entities


def _types(entities, entity_type):
    return [e for e in entities if e.entity_type == entity_type]


def test_extracts_cantidad_and_unidad_together() -> None:
    entities = extract_text_entities("se requieren 50 kg de material")

    cantidades = _types(entities, "cantidad")
    unidades = _types(entities, "unidad")
    assert len(cantidades) == 1 and cantidades[0].value == "50 kg"
    assert cantidades[0].normalized_value == "50"
    assert len(unidades) == 1 and unidades[0].normalized_value == "kg"
    assert cantidades[0].start_offset == unidades[0].start_offset


def test_no_cantidad_without_unit_nearby() -> None:
    entities = extract_text_entities("el codigo es 12345")

    assert _types(entities, "cantidad") == []


def test_extracts_numeric_date() -> None:
    entities = extract_text_entities("el plazo vence el 15/03/2026")

    fechas = _types(entities, "fecha")
    assert len(fechas) == 1
    assert fechas[0].value == "15/03/2026"
    assert fechas[0].confidence_score == 0.9


def test_extracts_long_form_date() -> None:
    entities = extract_text_entities("licitacion publicada el 5 de marzo de 2026")

    fechas = _types(entities, "fecha")
    assert len(fechas) == 1
    assert fechas[0].value == "5 de marzo de 2026"


def test_no_fecha_for_plain_number() -> None:
    entities = extract_text_entities("total 2026 unidades disponibles")

    assert _types(entities, "fecha") == []


def test_extracts_monto_with_dollar_sign() -> None:
    entities = extract_text_entities("presupuesto referencial $1.500.000")

    montos = _types(entities, "monto")
    assert len(montos) == 1
    assert montos[0].value == "$1.500.000"


def test_monto_does_not_swallow_a_trailing_sentence_comma() -> None:
    """Regression: found against real data — '$1.500.000,' kept the comma
    that separates it from the next clause, not a thousands separator."""
    entities = extract_text_entities("presupuesto $1.500.000, plazo de entrega hasta el 15/03/2026")

    montos = _types(entities, "monto")
    assert len(montos) == 1
    assert montos[0].value == "$1.500.000"


def test_extracts_monto_with_currency_word() -> None:
    entities = extract_text_entities("valor estimado 500 UF para el contrato")

    montos = _types(entities, "monto")
    assert len(montos) == 1
    assert "UF" in montos[0].value


def test_extracts_marca_and_modelo_with_explicit_keyword() -> None:
    entities = extract_text_entities("silla de ruedas marca Invacare modelo Action 3")

    marcas = _types(entities, "marca")
    modelos = _types(entities, "modelo")
    assert len(marcas) == 1 and marcas[0].value == "Invacare"
    assert marcas[0].confidence_score == 0.6
    assert len(modelos) == 1 and modelos[0].value.startswith("Action")


def test_modelo_capture_stops_at_punctuation() -> None:
    """Regression: found against real data — the capture crossed a comma
    into the next clause ('Action 3, presupuesto' instead of 'Action 3')."""
    entities = extract_text_entities("modelo Action 3, presupuesto referencial $100")

    modelos = _types(entities, "modelo")
    assert len(modelos) == 1
    assert modelos[0].value == "Action 3"


def test_marca_does_not_match_the_plural_marcas() -> None:
    """Regression: \\bmarca without a trailing \\b matched the "marca" prefix
    inside "marcas" (same class of bug as 6.7's "to" abbreviation)."""
    entities = extract_text_entities("texto sin marcas ni cantidades")

    assert _types(entities, "marca") == []


def test_no_marca_without_keyword() -> None:
    entities = extract_text_entities("silla de ruedas Invacare Action 3")

    assert _types(entities, "marca") == []
    assert _types(entities, "modelo") == []


def test_empty_text_returns_no_entities() -> None:
    assert extract_text_entities("") == ()
