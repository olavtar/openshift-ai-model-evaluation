# This project was developed with assistance from AI tools.

# Model Evaluation API

FastAPI backend for the OpenShift AI Model Evaluation QuickStart. Handles document ingestion, RAG retrieval, model evaluation via DeepEval, and comparison verdicts.

Key routes:
- **evaluation**: Create/compare eval runs, synthesize questions
- **documents**: Upload/chunk/embed PDFs
- **models**: List available models from MaaS
- **query**: RAG chat endpoint
- **health**: Liveness and readiness probes

> **Setup & Installation**: See the [root README](../../README.md) for installation and quick start instructions.

## Architecture Overview

This API package follows FastAPI best practices with a modular, async-first architecture:

```
Request → Router → Route Handler → Schema Validation → Business Logic → Response
                                                              ↓
                                                         Database (if enabled)
```

### Key Architectural Patterns

- **Dependency Injection**: FastAPI's dependency system for database sessions, authentication, and shared resources
- **Async/Await**: All route handlers use `async def` for non-blocking I/O operations
- **Pydantic Schemas**: Request/response validation and serialization
- **Router Organization**: Routes grouped by domain in separate modules
- **Configuration Management**: Centralized settings via Pydantic Settings

- **Database Integration**: Async SQLAlchemy with connection pooling via dependency injection

## Directory Structure

```
src/
├── main.py              # FastAPI app, middleware, router registration
├── core/
│   └── config.py        # Pydantic Settings (model endpoints, tokens, etc.)
├── routes/
│   ├── evaluation.py    # Eval runs: create, list, compare, synthesize questions
│   ├── documents.py     # PDF upload, chunking, embedding
│   ├── models.py        # List available models from MaaS
│   ├── query.py         # RAG chat endpoint
│   └── health.py        # Liveness and readiness probes
├── schemas/
│   ├── evaluation.py    # EvalRun, ComparisonResponse, ComparisonDecision, etc.
│   ├── documents.py     # Document upload/response schemas
│   └── ...
├── services/
│   ├── scoring.py       # DeepEval metrics (MaaSJudgeModel)
│   ├── verdicts.py      # Verdict computation, comparison decisions
│   ├── retrieval.py     # Hybrid retrieval (vector + keyword)
│   ├── generation.py    # Model answer generation
│   ├── profiles.py      # Evaluation profile loader (YAML)
│   ├── synthesizer.py   # Auto-generate questions from documents
│   ├── chunking.py      # PDF text extraction and chunking
│   └── embedding.py     # Vector embedding via MaaS
├── profiles/
│   └── fsi_compliance_v1.yaml  # FSI evaluation profile
└── admin.py             # SQLAdmin configuration
```

### Directory Purposes

- **`src/main.py`**: Application entry point where the FastAPI app is created, middleware configured, and routers are registered. This is where you add new route modules.

- **`src/core/`**: Core application infrastructure. Currently contains configuration management via Pydantic Settings.

- **`src/routes/`**: Route handlers organized by domain. Each file defines an `APIRouter` instance with related endpoints. Routers are registered in `main.py`.

- **`src/schemas/`**: Pydantic models for request/response validation. Schemas ensure type safety and automatic API documentation generation.

- **`src/models/`**: SQLAlchemy ORM models. See the [DB package README](../../db/README.md) for details on creating models.

- **`tests/`**: Test files mirror the `src/` structure. Each route module should have a corresponding test file.

## Adding New Endpoints

Follow these steps to add a new API endpoint:

### 1. Create Pydantic Schemas

Define request/response models in `src/schemas/`:

```python
# src/schemas/users.py
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
```

### 2. Create Route Module

Create a new router file in `src/routes/`:

```python
# src/routes/users.py
from fastapi import APIRouter
from ..schemas.users import UserCreate, UserResponse

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate) -> UserResponse:
    # Business logic here
    return UserResponse(id=1, email=user.email, name=user.name)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    # Business logic here
    return UserResponse(id=user_id, email="example@example.com", name="Example")
```

### 3. Register Router in Main App

Add the router to `src/main.py`:

```python
from .routes import health, users

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(users.router, prefix="/users", tags=["users"])
```

### 4. Add Tests

Create a test file in `tests/`:

```python
# tests/test_users.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/users/", json={
            "email": "test@example.com",
            "name": "Test User"
        })
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
```

## Using Database Models

When the DB package is enabled, database models are created in the DB package. See the [DB package README](../../db/README.md) for details on creating models and migrations.

### Using Models in API Routes

To use database models in your API routes, use FastAPI's dependency injection:

```python
# src/routes/users.py
from fastapi import APIRouter, Depends
from db import DatabaseService, get_db_service
from ..schemas.users import UserResponse

router = APIRouter()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db_service: DatabaseService = Depends(get_db_service)
) -> UserResponse:
    # Use db_service to query the database
    user = await db_service.get_user(user_id)
    return UserResponse(id=user.id, email=user.email, name=user.name)
```

The `get_db_service` dependency provides a database session with connection pooling and proper lifecycle management.

## Testing Patterns

### Test Structure

Tests use `pytest` with `pytest-asyncio` for async support. The test structure mirrors the source code:

```python
# tests/test_users.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_endpoint_name():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/endpoint")
        assert response.status_code == 200
```

### Common Test Patterns

**Testing async endpoints:**
```python
@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/async-endpoint")
        assert response.status_code == 200
```

**Testing with request bodies:**
```python
@pytest.mark.asyncio
async def test_post_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/endpoint", json={"key": "value"})
        assert response.status_code == 200
```

**Testing with database (transaction rollback):**
```python
@pytest.mark.asyncio
async def test_with_db(db_session):
    # db_session is automatically rolled back after test
    # Use it to test database operations
    pass
```

### Running Tests

```bash
pnpm test                        # Run all tests (recommended)
uv run pytest                    # Direct pytest command
uv run pytest tests/test_users.py # Run specific test file
uv run pytest -v                 # Verbose output
uv run pytest --cov=src         # With coverage
uv run pytest -k "health"       # Run tests matching pattern
```

## Configuration Architecture

Configuration is managed through Pydantic Settings in `src/core/config.py`:

```python
# src/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "model-evaluation"
    DEBUG: bool = False
    ALLOWED_HOSTS: list[str] = ["http://localhost:5173"]
    DATABASE_URL: str = "postgresql+asyncpg://..."

    class Config:
        env_file = ".env"

settings = Settings()
```

### Environment Variables

Settings are loaded from:
1. Default values in the `Settings` class
2. `.env` file in the project root
3. Environment variables (override `.env`)

Key environment variables:
- `ALLOWED_HOSTS` - Comma-separated list of allowed CORS origins
- `DATABASE_URL` - PostgreSQL connection string
- `DB_ECHO` - Enable SQL query logging (for debugging)

Access settings in your code:
```python
from ..core.config import settings

# Use settings.ALLOWED_HOSTS, settings.DEBUG, etc.
```

## Essential Scripts

```bash
# Development
uv run uvicorn src.main:app --reload  # Start dev server

# Testing
uv run pytest                          # Run tests
uv run pytest --cov=src               # With coverage

# Code Quality
uv run ruff check .                    # Lint
uv run ruff format .                  # Format
uv run mypy src/                       # Type check
```

For database-related scripts, see the [DB package README](../../db/README.md).

---

Generated with [AI QuickStart CLI](https://github.com/TheiaSurette/quickstart-cli)
