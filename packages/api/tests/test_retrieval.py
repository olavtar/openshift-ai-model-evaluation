# This project was developed with assistance from AI tools.
"""Tests for retrieval service."""

from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.retrieval import _fallback_search, retrieve_chunks


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


Row = namedtuple("Row", ["id", "text", "source_document", "page_number"])


def test_fallback_search_returns_chunks(mock_session):
    """Should return recent chunks when vector search is unavailable."""
    mock_rows = [
        Row(id=1, text="chunk one", source_document="doc.pdf", page_number="1"),
        Row(id=2, text="chunk two", source_document="doc.pdf", page_number="2"),
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
        Row(id=1, text="fallback chunk", source_document="doc.pdf", page_number="1"),
    ]
    mock_session.execute.return_value = _make_mock_result(mock_rows)

    import asyncio

    with patch("src.services.retrieval.generate_embeddings", return_value=None):
        result = asyncio.run(retrieve_chunks("test query", mock_session))

    assert len(result) == 1
    assert result[0]["text"] == "fallback chunk"
    assert result[0]["score"] == 0.0
