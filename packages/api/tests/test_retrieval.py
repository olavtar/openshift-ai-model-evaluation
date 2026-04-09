# This project was developed with assistance from AI tools.
"""Tests for retrieval service."""

from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.embedding import EmbeddingsResult
from src.services.retrieval import (
    _apply_diversity,
    _fallback_search,
    _reciprocal_rank_fusion,
    retrieve_chunks,
)


@pytest.fixture
def mock_session():
    """Create a mock async session with sync .all() on results."""
    session = AsyncMock()
    return session


def _make_mock_result(rows):
    """Create a mock query result where .all() is sync (like SQLAlchemy)."""
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    return mock_result


Row = namedtuple("Row", ["id", "text", "source_document", "page_number", "section_path"])


def test_fallback_search_returns_chunks(mock_session):
    """Should return recent chunks when vector search is unavailable."""
    mock_rows = [
        Row(id=1, text="chunk one", source_document="doc.pdf", page_number="1", section_path=None),
        Row(
            id=2, text="chunk two", source_document="doc.pdf", page_number="2", section_path=None
        ),
    ]
    mock_session.execute.return_value = _make_mock_result(mock_rows)

    import asyncio

    result = asyncio.run(_fallback_search(mock_session, top_k=5))

    assert len(result) == 2
    assert result[0]["text"] == "chunk one"
    assert result[0]["score"] == 0.0
    assert result[1]["source_document"] == "doc.pdf"


def test_retrieve_chunks_uses_fallback_when_no_embeddings(mock_session):
    """Should fall back to recent chunks when embedding generation fails."""
    mock_rows = [
        Row(
            id=1,
            text="fallback chunk",
            source_document="doc.pdf",
            page_number="1",
            section_path=None,
        ),
    ]
    mock_session.execute.return_value = _make_mock_result(mock_rows)

    import asyncio

    with patch(
        "src.services.retrieval.generate_embeddings",
        new_callable=AsyncMock,
        return_value=EmbeddingsResult(vectors=None, error=None),
    ):
        result = asyncio.run(retrieve_chunks("test query", mock_session))

    assert len(result) == 1
    assert result[0]["text"] == "fallback chunk"
    assert result[0]["score"] == 0.0


# --- RRF and diversity tests ---


def _chunk(chunk_id, doc="doc.pdf", score=0.5):
    return {
        "id": chunk_id,
        "text": f"chunk {chunk_id}",
        "source_document": doc,
        "page_number": "1",
        "section_path": None,
        "score": score,
    }


def test_rrf_merges_two_lists():
    """Should merge and re-rank results from two lists using RRF."""
    vector = [_chunk(1, score=0.9), _chunk(2, score=0.8), _chunk(3, score=0.7)]
    keyword = [_chunk(2, score=0.6), _chunk(4, score=0.5), _chunk(1, score=0.4)]

    merged = _reciprocal_rank_fusion(vector, keyword)

    # Chunks 1 and 2 appear in both lists, so they should rank higher
    ids = [c["id"] for c in merged]
    assert ids[0] in (1, 2)  # top should be one shared between lists
    assert 4 in ids  # keyword-only result should still appear


def test_rrf_single_list():
    """Should preserve order when only one list is provided."""
    results = [_chunk(1, score=0.9), _chunk(2, score=0.8)]
    merged = _reciprocal_rank_fusion(results)
    assert [c["id"] for c in merged] == [1, 2]


def test_diversity_caps_per_doc():
    """Should cap chunks per document."""
    chunks = [
        _chunk(1, doc="a.pdf"),
        _chunk(2, doc="a.pdf"),
        _chunk(3, doc="a.pdf"),
        _chunk(4, doc="b.pdf"),
    ]
    result = _apply_diversity(chunks, top_k=3, max_per_doc=2, diversity_min=1)
    a_count = sum(1 for c in result if c["source_document"] == "a.pdf")
    assert a_count <= 2


def test_diversity_promotes_underrepresented_docs():
    """Should promote chunks from underrepresented documents."""
    chunks = [
        _chunk(1, doc="a.pdf"),
        _chunk(2, doc="a.pdf"),
        _chunk(3, doc="a.pdf"),
        _chunk(4, doc="a.pdf"),
        _chunk(5, doc="b.pdf"),
        _chunk(6, doc="c.pdf"),
    ]
    result = _apply_diversity(chunks, top_k=4, max_per_doc=2, diversity_min=3)
    docs = {c["source_document"] for c in result}
    assert len(docs) >= 3  # should include a, b, c


def test_diversity_returns_empty_for_empty_input():
    """Should return empty list for no chunks."""
    assert _apply_diversity([], top_k=5, max_per_doc=2, diversity_min=3) == []


def test_retrieve_chunks_hybrid_path(mock_session):
    """Should merge vector and keyword results via RRF when embeddings succeed."""
    import asyncio

    vector_results = [_chunk(1, doc="a.pdf"), _chunk(2, doc="b.pdf")]
    keyword_results = [_chunk(2, doc="b.pdf"), _chunk(3, doc="c.pdf")]

    with (
        patch(
            "src.services.retrieval.generate_embeddings",
            new_callable=AsyncMock,
            return_value=EmbeddingsResult(vectors=[[0.1, 0.2]], error=None),
        ),
        patch(
            "src.services.retrieval._vector_search",
            new_callable=AsyncMock,
            return_value=vector_results,
        ),
        patch(
            "src.services.retrieval._keyword_search",
            new_callable=AsyncMock,
            return_value=keyword_results,
        ),
    ):
        result = asyncio.run(retrieve_chunks("test query", mock_session, top_k=5))

    ids = [c["id"] for c in result]
    # Chunk 2 appears in both lists so should rank highest after RRF
    assert ids[0] == 2
    # All 3 chunks should appear
    assert set(ids) == {1, 2, 3}


def test_keyword_search_returns_empty_on_exception(mock_session):
    """Should gracefully return empty list when keyword search fails."""
    import asyncio

    from src.services.retrieval import _keyword_search

    mock_session.execute.side_effect = Exception("full-text search not supported")

    result = asyncio.run(_keyword_search("test query", mock_session, limit=10))
    assert result == []
