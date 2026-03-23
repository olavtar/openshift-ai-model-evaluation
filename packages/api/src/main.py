# This project was developed with assistance from AI tools.
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import setup_admin
from .core.config import settings
from .routes import health

app = FastAPI(
    title="OpenShift AI Model Evaluation API",
    description="API for evaluating and comparing AI models on OpenShift AI",
    version="0.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])

setup_admin(app)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to OpenShift AI Model Evaluation API"}
