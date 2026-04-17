# This project was developed with assistance from AI tools.
"""Tests for coverage gap detection service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.coverage import detect_coverage_gaps


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


def test_returns_none_when_no_model():
    """Should return None when no model is configured."""
    from src.core.config import settings

    settings.JUDGE_MODEL_NAME = ""
    settings.API_TOKEN = ""

    result = asyncio.run(
        detect_coverage_gaps("expected answer", "actual answer")
    )
    assert result is None


def test_returns_none_when_no_token():
    """Should return None when no API token is set."""
    from src.core.config import settings

    settings.JUDGE_MODEL_NAME = "test-model"
    settings.API_TOKEN = ""

    result = asyncio.run(
        detect_coverage_gaps("expected answer", "actual answer")
    )
    assert result is None


def test_returns_coverage_report_on_success():
    """Should return structured coverage report with concepts, covered, and missing."""
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
                    "content": '{"concepts": ['
                    '{"text": "Rule 6c-11 provisions", "status": "covered"}, '
                    '{"text": "N-PORT filing deadlines", "status": "missing"}, '
                    '{"text": "SAI disclosure requirements", "status": "covered"}'
                    "]}"
                }
            }
        ]
    }

    with patch("src.services.coverage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            detect_coverage_gaps(
                "Rule 6c-11 provisions, N-PORT filing deadlines, SAI disclosures",
                "The answer covers Rule 6c-11 and SAI requirements.",
            )
        )

    assert result is not None
    assert len(result["concepts"]) == 3
    assert len(result["covered"]) == 2
    assert len(result["missing"]) == 1
    assert "N-PORT filing deadlines" in result["missing"]
    assert result["coverage_ratio"] == pytest.approx(2 / 3)


def test_returns_none_on_invalid_json():
    """Should return None when LLM returns invalid JSON."""
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

    with patch("src.services.coverage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            detect_coverage_gaps("expected", "actual")
        )

    assert result is None


def test_returns_none_on_api_error():
    """Should return None when API call fails."""
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

    with patch("src.services.coverage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            detect_coverage_gaps("expected", "actual")
        )

    assert result is None


def test_handles_markdown_fenced_json():
    """Should strip markdown fencing and parse the JSON."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    fenced_content = (
        "```json\n"
        '{"concepts": [{"text": "concept A", "status": "covered"}]}\n'
        "```"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": fenced_content}}]
    }

    with patch("src.services.coverage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            detect_coverage_gaps("expected", "actual")
        )

    assert result is not None
    assert len(result["concepts"]) == 1
    assert result["coverage_ratio"] == 1.0


def test_returns_none_on_empty_concepts():
    """Should return None when LLM returns empty concepts list."""
    from src.core.config import settings

    settings.API_TOKEN = "test-token"
    settings.MAAS_ENDPOINT = "https://example.com"
    settings.JUDGE_MODEL_NAME = "test-model"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"concepts": []}'}}]
    }

    with patch("src.services.coverage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            detect_coverage_gaps("expected", "actual")
        )

    assert result is None
