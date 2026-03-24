# This project was developed with assistance from AI tools.
"""Tests for text chunking service."""

from src.services.chunking import CHUNK_OVERLAP, CHUNK_SIZE, chunk_text


def test_short_text_returns_single_chunk():
    """Should return one chunk when text is shorter than chunk_size."""
    result = chunk_text("Hello world", source_document="test.pdf")
    assert len(result) == 1
    assert result[0]["text"] == "Hello world"
    assert result[0]["token_count"] == 2
    assert result[0]["source_document"] == "test.pdf"


def test_empty_text_returns_empty():
    """Should return no chunks for empty text."""
    assert chunk_text("", source_document="test.pdf") == []
    assert chunk_text("   ", source_document="test.pdf") == []


def test_long_text_produces_multiple_chunks():
    """Should split long text into overlapping chunks."""
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)
    result = chunk_text(text, source_document="test.pdf")

    assert len(result) > 1
    # Each chunk should be at most chunk_size words
    for chunk in result:
        assert chunk["token_count"] <= CHUNK_SIZE


def test_chunks_overlap():
    """Consecutive chunks should share overlapping words."""
    words = [f"w{i}" for i in range(1024)]
    text = " ".join(words)
    result = chunk_text(text, source_document="test.pdf", chunk_size=512, chunk_overlap=64)

    assert len(result) >= 2
    first_words = set(result[0]["text"].split())
    second_words = set(result[1]["text"].split())
    overlap = first_words & second_words
    assert len(overlap) >= 64


def test_page_number_preserved():
    """Should preserve page number in chunk metadata."""
    result = chunk_text("Some text", source_document="doc.pdf", page_number="3")
    assert result[0]["page_number"] == "3"


def test_all_text_covered():
    """Every word from the input should appear in at least one chunk."""
    words = [f"w{i}" for i in range(800)]
    text = " ".join(words)
    result = chunk_text(text, source_document="test.pdf")

    all_chunk_words = set()
    for chunk in result:
        all_chunk_words.update(chunk["text"].split())

    assert all_chunk_words == set(words)
