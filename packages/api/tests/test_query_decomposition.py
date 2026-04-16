# This project was developed with assistance from AI tools.
"""Tests for query decomposition service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.query_decomposition import decompose_query


@pytest.fixture(autouse=True)
def _reset_settings():
    """Ensure settings are restored after each test."""
    from src.core.config import settings

    original_token = settings.API_TOKEN
    original_maas = settings.MAAS_ENDPOINT
    original_judge = settings.JUDGE_MODEL_NAME
    yield
    settings.API_TOKEN = original_token
    settings.MAAS_ENDPOINT = original_maas
    settings.JUDGE_MODEL_NAME = original_judge


def test_returns_original_when_no_model():
    """Should return original question when no model is configured."""
    from src.core.config import settings

    settings.JUDGE_MODEL_NAME = ""
    settings.API_TOKEN = ""

    result = asyncio.run(decompose_query("broad question"))
    assert result == ["broad question"]


def test_returns_original_when_no_token():
    """Should return original question when no API token is set."""
    from src.core.config import settings

    settings.JUDGE_MODEL_NAME = "test-model"
    settings.API_TOKEN = ""

    result = asyncio.run(decompose_query("broad question"))
    assert result == ["broad question"]


def test_returns_sub_queries_on_success():
    """Should return parsed sub-queries from LLM response."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '["What is Rule 6c-11?", "What are SAI requirements?", "What are N-PORT filings?"]'
                }
            }
        ]
    }

    with patch("src.services.query_decomposition.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(decompose_query("What is the ETF regulatory framework?"))

    assert len(result) == 3
    assert "Rule 6c-11" in result[0]
    assert "SAI" in result[1]


def test_returns_original_on_invalid_json():
    """Should fall back to original question when LLM returns invalid JSON."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "This is not JSON"}}]
    }

    with patch("src.services.query_decomposition.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(decompose_query("broad question"))

    assert result == ["broad question"]


def test_returns_original_on_api_error():
    """Should fall back to original question when API call fails."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch("src.services.query_decomposition.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(decompose_query("broad question"))

    assert result == ["broad question"]


def test_respects_max_sub_queries():
    """Should cap the number of sub-queries returned."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '["q1", "q2", "q3", "q4", "q5", "q6", "q7"]'
                }
            }
        ]
    }

    with patch("src.services.query_decomposition.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(decompose_query("broad question", max_sub_queries=3))

    assert len(result) <= 3


def test_returns_original_on_empty_array():
    """Should fall back when LLM returns empty array."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "[]"}}]
    }

    with patch("src.services.query_decomposition.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(decompose_query("broad question"))

    assert result == ["broad question"]
