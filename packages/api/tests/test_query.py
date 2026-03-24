# This project was developed with assistance from AI tools.
"""Tests for the RAG query endpoint (/query)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db import Base, get_db
from src.main import app


# --- Fixtures ---


@pytest.fixture
def _setup_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import asyncio

    asyncio.run(_create_tables(engine))

    return engine, async_session


async def _create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client(_setup_db):
    """FastAPI test client with DB dependency overridden."""
    engine, async_session = _setup_db

    async def _override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Tests ---


def test_query_returns_answer(client):
    """Should return an answer with sources from the RAG pipeline."""
    mock_chunks = [
        {"id": 1, "text": "Revenue was $1B.", "source_document": "report.pdf", "page_number": "5", "score": 0.92},
    ]
    mock_generation = {
        "answer": "Revenue was $1 billion.",
        "model": "granite-3.1-8b-instruct",
        "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
    }

    with (
        patch("src.routes.query.retrieve_chunks", return_value=mock_chunks),
        patch("src.routes.query.generate_answer", return_value=mock_generation),
    ):
        response = client.post(
            "/query/",
            json={"question": "What was the revenue?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Revenue was $1 billion."
    assert data["model"] == "granite-3.1-8b-instruct"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_document"] == "report.pdf"
    assert data["sources"][0]["score"] == 0.92
    assert data["usage"]["total_tokens"] == 60


def test_query_with_custom_model(client):
    """Should use the specified model for generation."""
    with (
        patch("src.routes.query.retrieve_chunks", return_value=[]),
        patch("src.routes.query.generate_answer", return_value={
            "answer": "No context available.",
            "model": "llama-3.1-8b-instruct",
            "usage": None,
        }) as mock_gen,
    ):
        response = client.post(
            "/query/",
            json={"question": "What?", "model_name": "llama-3.1-8b-instruct"},
        )

    assert response.status_code == 200
    assert response.json()["model"] == "llama-3.1-8b-instruct"
    mock_gen.assert_called_once()
    assert mock_gen.call_args[1]["model_name"] == "llama-3.1-8b-instruct"


def test_query_validates_empty_question(client):
    """Should reject empty questions."""
    response = client.post("/query/", json={"question": ""})
    assert response.status_code == 422


def test_query_with_no_sources(client):
    """Should return answer even when no chunks are retrieved."""
    with (
        patch("src.routes.query.retrieve_chunks", return_value=[]),
        patch("src.routes.query.generate_answer", return_value={
            "answer": "I don't have enough context to answer.",
            "model": "granite-3.1-8b-instruct",
            "usage": None,
        }),
    ):
        response = client.post(
            "/query/",
            json={"question": "Unknown topic?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == []
    assert data["usage"] is None
