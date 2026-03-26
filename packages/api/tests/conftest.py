"""
Pytest configuration and fixtures
"""

import pytest
from db import Base, get_db
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.main import app


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


@pytest.fixture
def health_response(client):
    """Get health check response data"""
    response = client.get("/health/ready")
    assert response.status_code == 200
    return response.json()
