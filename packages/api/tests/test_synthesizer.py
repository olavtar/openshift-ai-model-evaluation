# This project was developed with assistance from AI tools.
"""Tests for question synthesizer endpoint and service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db import Base, Chunk, Document, get_db
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


# --- Tests ---


def test_synthesize_returns_questions(client, _setup_db):
    """Should return generated questions from document chunks."""
    _, async_session = _setup_db
    _seed_documents_and_chunks(async_session)

    mock_golden = MagicMock()
    mock_golden.input = "What is artificial intelligence?"
    mock_golden.expected_output = "AI is the simulation of human intelligence by machines."

    with (
        patch("src.services.synthesizer.MaaSJudgeModel"),
        patch("src.services.synthesizer.Synthesizer") as mock_synth_cls,
    ):
        mock_synth = MagicMock()
        mock_synth.generate_goldens.return_value = [mock_golden]
        mock_synth_cls.return_value = mock_synth

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
    with (
        patch("src.services.synthesizer.MaaSJudgeModel"),
        patch("src.services.synthesizer.Synthesizer"),
    ):
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

    mock_golden = MagicMock()
    mock_golden.input = "What is ML?"
    mock_golden.expected_output = "Machine learning is a subset of AI."

    with (
        patch("src.services.synthesizer.MaaSJudgeModel"),
        patch("src.services.synthesizer.Synthesizer") as mock_synth_cls,
    ):
        mock_synth = MagicMock()
        mock_synth.generate_goldens.return_value = [mock_golden]
        mock_synth_cls.return_value = mock_synth

        response = client.post(
            "/evaluations/synthesize",
            json={"document_ids": [1], "max_questions": 5},
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_synthesize_filters_nonexistent_document(client):
    """Should return empty when filtering by document ID with no chunks."""
    with (
        patch("src.services.synthesizer.MaaSJudgeModel"),
        patch("src.services.synthesizer.Synthesizer"),
    ):
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
