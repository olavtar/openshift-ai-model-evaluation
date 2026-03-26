# This project was developed with assistance from AI tools.
"""Tests for embedding service."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.embedding import generate_embeddings


@pytest.fixture(autouse=True)
def _reset_settings():
    """Ensure settings are restored after each test."""
    from src.core.config import settings

    original_token = settings.MODEL_API_TOKEN
    yield
    settings.MODEL_API_TOKEN = original_token


def test_returns_none_when_no_token():
    """Should skip embeddings when MODEL_API_TOKEN is empty."""
    from src.core.config import settings

    settings.MODEL_API_TOKEN = ""

    import asyncio

    result = asyncio.run(generate_embeddings(["hello"]))
    assert result is None


def test_returns_embeddings_on_success():
    """Should return embeddings from the API response."""
    from unittest.mock import MagicMock

    from src.core.config import settings

    settings.MODEL_API_TOKEN = "test-token"

    # httpx response is sync (not async), so use MagicMock for .json()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"embedding": [0.1, 0.2, 0.3], "index": 0},
            {"embedding": [0.4, 0.5, 0.6], "index": 1},
        ]
    }

    import asyncio

    with patch("src.services.embedding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(generate_embeddings(["hello", "world"]))

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_returns_none_on_api_error():
    """Should return None when the API returns an error."""
    from unittest.mock import MagicMock

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

    with patch("src.services.embedding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(generate_embeddings(["hello"]))

    assert result is None
