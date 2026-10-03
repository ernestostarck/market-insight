from app.nlp.preprocessing import TextPreprocessor, tokenize


def test_preprocess_preserves_source_and_normalizes_html_whitespace() -> None:
    source = "<p>Adquisición&nbsp; de la\n <strong>Sillas</strong>  Ruedas</p>\x00"
    result = TextPreprocessor().preprocess(source)
    assert result.original_text == source
    assert result.normalized_text == "adquisición de la sillas ruedas"
    assert result.language == "es"


def test_build_tender_document_combines_searchable_fields() -> None:
    result = TextPreprocessor().build_tender_document(
        title="Compra de computadores", description=None, item_texts=["Notebook", None, "Monitor"]
    )
    assert result.normalized_text == "titulo: compra de computadores item: notebook item: monitor"


def test_preprocess_replaces_unrecoverable_replacement_characters() -> None:
    result = TextPreprocessor().preprocess("Educaci�n P�blica")
    assert "�" not in result.normalized_text
    assert result.normalized_text == "educaci n p blica"


def test_preprocess_strips_invisible_characters() -> None:
    result = TextPreprocessor().preprocess("Compra​ de﻿ sillas")
    assert result.normalized_text == "compra de sillas"


def test_preprocess_strips_decorative_bullets_but_keeps_meaningful_punctuation() -> None:
    result = TextPreprocessor().preprocess("• Sillas 50% de descuento, modelo A/B")
    assert result.normalized_text == "sillas 50% de descuento, modelo a/b"


def test_preprocess_expands_numero_abbreviation_only_before_digits() -> None:
    degree_sign = TextPreprocessor().preprocess("Linea N°1: telas")
    assert degree_sign.normalized_text == "linea numero 1: telas"

    # "Nº" (ordinal indicator) becomes "No" after NFKC — must still be caught.
    ordinal = TextPreprocessor().preprocess("Linea Nº2: telas")
    assert ordinal.normalized_text == "linea numero 2: telas"


def test_preprocess_does_not_corrupt_negation() -> None:
    result = TextPreprocessor().preprocess("No aplica")
    assert result.normalized_text == "no aplica"

    result = TextPreprocessor().preprocess("No hay observaciones")
    assert "numero" not in result.normalized_text


def test_preprocess_normalizes_weight_length_and_area_units() -> None:
    result = TextPreprocessor().preprocess("10 kgs de arroz y 5 mts de cable, 3 lt de agua")
    assert result.normalized_text == "10 kg de arroz y 5 m de cable, 3 l de agua"

    result = TextPreprocessor().preprocess("Area de 20 m2 y 15 mt2")
    assert result.normalized_text == "area de 20 m2 y 15 m2"


def test_preprocess_normalizes_units_with_trailing_period() -> None:
    result = TextPreprocessor().preprocess("5 kg. de arroz y 3 mts. de cable")
    assert result.normalized_text == "5 kg de arroz y 3 m de cable"


def test_preprocess_normalizes_unidad_only_when_attached_to_a_number() -> None:
    result = TextPreprocessor().preprocess("cantidad: 10un, 5 und. y 2 unid")
    assert result.normalized_text == "cantidad: 10 unidad, 5 unidad y 2 unidad"

    # "un" as the indefinite article must never be touched.
    result = TextPreprocessor().preprocess("un producto de calidad")
    assert result.normalized_text == "un producto de calidad"


def test_tokenize_splits_normalized_text_into_words() -> None:
    assert tokenize("sillas de ruedas 10 unidad") == ("sillas", "de", "ruedas", "10", "unidad")


def test_detect_language_handles_short_text_with_a_single_marker() -> None:
    assert TextPreprocessor().preprocess("Compra de sillas").language == "es"


def test_detect_language_returns_und_for_non_spanish_or_empty_text() -> None:
    assert TextPreprocessor().preprocess("Notebook").language == "und"
    assert TextPreprocessor().preprocess("").language == "und"


# --- Real ChileCompra data (licitacion 1002588-89-LE26, verified via the
# public API this session — see docs/07-ai/text-preprocessing.md) ---


def test_preprocess_on_real_licitacion_descripcion() -> None:
    real_descripcion = (
        "Adquirir materiales e insumos para talleres extraescolares de los "
        "establecimientos educacionales del Servicio Local de Educación "
        "Pública Puerto Cordillera."
    )
    result = TextPreprocessor().preprocess(real_descripcion)
    assert "�" not in result.normalized_text
    assert "educación pública" in result.normalized_text
    assert result.language == "es"


def test_preprocess_on_real_item_descripcion_normalizes_numero() -> None:
    real_item_descripcion = "Línea N°1: Telas e insumos para taller de teatro Escuela Aníbal Pinto"
    result = TextPreprocessor().preprocess(real_item_descripcion)
    assert "numero 1" in result.normalized_text
    assert result.language == "es"
