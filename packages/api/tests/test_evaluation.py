# This project was developed with assistance from AI tools.
"""Tests for evaluation endpoints (/evaluations)."""

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


def test_create_eval_run(client):
    """Should create an evaluation run and return its ID."""
    # Mock background task so it doesn't actually run
    with patch("src.routes.evaluation._run_evaluation"):
        response = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?", "Explain RAG."],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["eval_run_id"] >= 1
    assert data["model_name"] == "granite-3.1-8b-instruct"
    assert data["status"] == "pending"
    assert data["total_questions"] == 2
    assert "2 questions" in data["message"]


def test_create_eval_run_validates_empty_questions(client):
    """Should reject empty questions list."""
    response = client.post(
        "/evaluations/",
        json={"model_name": "granite-3.1-8b-instruct", "questions": []},
    )
    assert response.status_code == 422


def test_list_eval_runs_empty(client):
    """Should return empty list when no runs exist."""
    response = client.get("/evaluations/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_eval_runs_after_create(client):
    """Should include created run in list."""
    with patch("src.routes.evaluation._run_evaluation"):
        client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )

    response = client.get("/evaluations/")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["model_name"] == "granite-3.1-8b-instruct"


def test_get_eval_run_by_id(client):
    """Should return eval run with its results."""
    with patch("src.routes.evaluation._run_evaluation"):
        create_resp = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )
    run_id = create_resp.json()["eval_run_id"]

    response = client.get(f"/evaluations/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["model_name"] == "granite-3.1-8b-instruct"
    assert "results" in data


def test_get_eval_run_not_found(client):
    """Should return 404 for non-existent eval run."""
    response = client.get("/evaluations/999")
    assert response.status_code == 404
