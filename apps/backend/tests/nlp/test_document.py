from app.nlp.document import DocumentChunk, TextChunker, build_document
from app.nlp.preprocessing import TextPreprocessor


def test_short_text_produces_a_single_chunk_covering_the_whole_text() -> None:
    text = "licitacion de sillas de ruedas para adultos mayores."
    chunks = TextChunker(max_chars=1000).split(text)

    assert chunks == (DocumentChunk(sequence=0, text=text, start_offset=0, end_offset=len(text)),)


def test_long_text_splits_on_sentence_boundaries_without_cutting_words() -> None:
    sentence = "adquisicion de insumos para rehabilitacion y movilidad reducida. "
    text = sentence * 20  # long enough to force multiple chunks at a small max_chars
    chunker = TextChunker(max_chars=120)

    chunks = chunker.split(text)

    assert len(chunks) > 1
    reconstructed = "".join(chunk.text for chunk in chunks)
    assert reconstructed == text
    for i in range(len(chunks) - 1):
        assert chunks[i].end_offset == chunks[i + 1].start_offset


def test_single_sentence_longer_than_max_chars_falls_back_to_word_boundaries() -> None:
    words = ["palabra" + str(i) for i in range(50)]
    text = " ".join(words)  # one run-on "sentence", no punctuation at all
    chunker = TextChunker(max_chars=30)

    chunks = chunker.split(text)

    assert len(chunks) > 1
    reconstructed = "".join(chunk.text for chunk in chunks)
    assert reconstructed == text
    # never split mid-word: every original word token appears whole in some chunk
    all_tokens = {token for chunk in chunks for token in chunk.text.split()}
    for word in words:
        assert word in all_tokens


def test_build_document_reuses_preprocessor_output_and_hashes_normalized_text() -> None:
    preprocessor = TextPreprocessor()
    preprocessed = preprocessor.build_tender_document(
        title="Adquisicion sillas de ruedas", description="Para centros de adultos mayores",
    )

    document = build_document(licitacion_id=42, preprocessed=preprocessed)

    assert document.licitacion_id == 42
    assert document.raw_text == preprocessed.original_text
    assert document.normalized_text == preprocessed.normalized_text
    assert document.language == preprocessed.language
    assert len(document.content_hash) == 64  # sha256 hex digest
    assert document.chunks


def test_content_hash_is_deterministic_and_sensitive_to_text_changes() -> None:
    preprocessor = TextPreprocessor()
    same_a = build_document(1, preprocessor.build_tender_document(title="Sillas de ruedas", description=None))
    same_b = build_document(1, preprocessor.build_tender_document(title="Sillas de ruedas", description=None))
    different = build_document(1, preprocessor.build_tender_document(title="Camas clinicas", description=None))

    assert same_a.content_hash == same_b.content_hash
    assert same_a.content_hash != different.content_hash
