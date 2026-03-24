# This project was developed with assistance from AI tools.
"""Tests for generation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.generation import _build_context_block, generate_answer


@pytest.fixture(autouse=True)
def _reset_settings():
    """Ensure settings are restored after each test."""
    from src.core.config import settings

    original_token = settings.MODEL_API_TOKEN
    yield
    settings.MODEL_API_TOKEN = original_token


def test_build_context_block_formats_chunks():
    """Should format chunks with source headers."""
    chunks = [
        {"source_document": "report.pdf", "page_number": "3", "text": "Revenue grew 10%."},
        {"source_document": "guide.pdf", "page_number": None, "text": "See section 4."},
    ]
    result = _build_context_block(chunks)
    assert "[Source 1: report.pdf, page 3]" in result
    assert "Revenue grew 10%." in result
    assert "[Source 2: guide.pdf]" in result
    assert "page" not in result.split("[Source 2:")[1].split("]")[0]


def test_returns_error_when_no_token():
    """Should return a helpful message when no API token is configured."""
    from src.core.config import settings

    settings.MODEL_API_TOKEN = ""

    import asyncio

    result = asyncio.run(generate_answer("What is X?", [], "granite-3.1-8b-instruct"))
    assert "No MODEL_API_TOKEN" in result["answer"]
    assert result["model"] == "granite-3.1-8b-instruct"


def test_returns_answer_on_success():
    """Should return the generated answer from the LLM."""
    from src.core.config import settings

    settings.MODEL_API_TOKEN = "test-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "The answer is 42."}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
    }

    import asyncio

    with patch("src.services.generation.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            generate_answer("What is the meaning?", [{"source_document": "doc.pdf", "page_number": "1", "text": "context"}], "granite-3.1-8b-instruct")
        )

    assert result["answer"] == "The answer is 42."
    assert result["model"] == "granite-3.1-8b-instruct"
    assert result["usage"]["total_tokens"] == 110


def test_returns_error_on_api_failure():
    """Should return error message when LLM API fails."""
    from src.core.config import settings

    settings.MODEL_API_TOKEN = "test-token"

    import asyncio
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch("src.services.generation.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            generate_answer("What?", [], "granite-3.1-8b-instruct")
        )

    assert "error" in result["answer"].lower() or "500" in result["answer"]
