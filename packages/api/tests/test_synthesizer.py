# This project was developed with assistance from AI tools.
"""Tests for question synthesizer endpoint and service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db import Chunk, Document

from src.core.config import settings


def _seed_documents_and_chunks(async_session):
    """Seed a document with chunks for synthesizer tests."""
    import asyncio

    async def _seed():
        async with async_session() as session:
            doc = Document(id=1, filename="test.pdf", status="ready", chunk_count=3)
            session.add(doc)
            await session.flush()

            for i in range(3):
                session.add(
                    Chunk(
                        document_id=1,
                        text=f"This is chunk {i} about artificial intelligence and machine learning.",
                        source_document="test.pdf",
                        element_type="paragraph",
                        token_count=10,
                    )
                )
            await session.commit()

    asyncio.run(_seed())


@pytest.fixture(autouse=True)
def _synthesis_env(monkeypatch):
    """Synthesis route requires a model name and MaaS settings."""
    monkeypatch.setattr(settings, "MODEL_A_NAME", "test-synth-model", raising=False)
    monkeypatch.setattr(settings, "API_TOKEN", "test-token", raising=False)
    monkeypatch.setattr(settings, "MAAS_ENDPOINT", "https://maas.test", raising=False)


def _patch_httpx_synthesize(questions_data):
    """Patch httpx.AsyncClient so POST returns JSON questions from the model."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"questions": questions_data})}}]
    }

    mock_inner = MagicMock()
    mock_inner.post = AsyncMock(return_value=mock_response)

    mock_ac = MagicMock()
    mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_inner)
    mock_ac.return_value.__aexit__ = AsyncMock(return_value=None)

    return patch("src.services.synthesizer.httpx.AsyncClient", mock_ac)


# --- Tests ---


def test_synthesize_returns_questions(client, _setup_db):
    """Should return generated questions from document chunks."""
    _, async_session = _setup_db
    _seed_documents_and_chunks(async_session)

    with _patch_httpx_synthesize([
        {
            "question": "What is artificial intelligence?",
            "expected_answer": "AI is the simulation of human intelligence by machines.",
        }
    ]):
        response = client.post(
            "/evaluations/synthesize",
            json={"max_questions": 5},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["questions"][0]["question"] == "What is artificial intelligence?"
    assert data["questions"][0]["expected_answer"] is not None


def test_synthesize_empty_when_no_documents(client):
    """Should return empty list when no documents exist."""
    response = client.post(
        "/evaluations/synthesize",
        json={"max_questions": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["questions"] == []


def test_synthesize_filters_by_document_ids(client, _setup_db):
    """Should only use chunks from specified document IDs."""
    _, async_session = _setup_db
    _seed_documents_and_chunks(async_session)

    with _patch_httpx_synthesize([
        {"question": "What is ML?", "expected_answer": "Machine learning is a subset of AI."}
    ]):
        response = client.post(
            "/evaluations/synthesize",
            json={"document_ids": [1], "max_questions": 5},
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_synthesize_filters_nonexistent_document(client):
    """Should return empty when filtering by document ID with no chunks."""
    response = client.post(
        "/evaluations/synthesize",
        json={"document_ids": [999], "max_questions": 5},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_synthesize_validates_max_questions(client):
    """Should reject max_questions outside 1-50 range."""
    response = client.post(
        "/evaluations/synthesize",
        json={"max_questions": 0},
    )
    assert response.status_code == 422

    response = client.post(
        "/evaluations/synthesize",
        json={"max_questions": 51},
    )
    assert response.status_code == 422


def test_parse_questions_json_raw():
    """Should parse raw JSON without fences."""
    from src.services.synthesizer import _parse_questions_json

    result = _parse_questions_json('{"questions": [{"question": "Q1"}]}')
    assert result["questions"][0]["question"] == "Q1"


def test_parse_questions_json_fenced():
    """Should parse JSON wrapped in markdown code fences."""
    from src.services.synthesizer import _parse_questions_json

    raw = '```json\n{"questions": [{"question": "Q2"}]}\n```'
    result = _parse_questions_json(raw)
    assert result["questions"][0]["question"] == "Q2"


def test_parse_questions_json_malformed():
    """Should raise on malformed JSON."""
    from src.services.synthesizer import _parse_questions_json

    with pytest.raises(json.JSONDecodeError):
        _parse_questions_json("not json at all")


def test_synthesize_rejects_when_no_model_configured(client, monkeypatch):
    """Should 400 when no synthesis model is configured."""
    monkeypatch.setattr(settings, "MODEL_A_NAME", "", raising=False)
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "", raising=False)
    monkeypatch.setattr(settings, "QUESTION_SYNTHESIS_MODEL_NAME", "", raising=False)

    response = client.post(
        "/evaluations/synthesize",
        json={"max_questions": 5},
    )
    assert response.status_code == 400
    assert "question synthesis" in response.json()["detail"].lower()
