# This project was developed with assistance from AI tools.
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import setup_admin
from .core.config import settings
from .core.errors import register_exception_handlers
from .core.logging import setup_logging
from .core.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from .routes import health

# Initialise structured JSON logging before anything else
setup_logging(level=settings.LOG_LEVEL)

app = FastAPI(
    title="OpenShift AI Model Evaluation API",
    description="API for evaluating and comparing AI models on OpenShift AI",
    version="0.0.0",
)

# -- Middleware (order matters: outermost middleware runs first) --
# Correlation ID must be added before request logging so the ID is available.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Exception handlers --
register_exception_handlers(app)

# -- Routers --
app.include_router(health.router, prefix="/health", tags=["health"])

# -- Admin dashboard --
setup_admin(app)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to OpenShift AI Model Evaluation API"}
