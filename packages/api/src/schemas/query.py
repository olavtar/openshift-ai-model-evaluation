# This project was developed with assistance from AI tools.
"""Pydantic schemas for the RAG query endpoint."""

from pydantic import BaseModel, Field

from ..core.config import settings


class SourceChunk(BaseModel):
    """A retrieved context chunk returned with the answer."""

    id: int
    text: str
    source_document: str
    page_number: str | None = None
    score: float


class UsageInfo(BaseModel):
    """Token usage information from the LLM."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class QueryRequest(BaseModel):
    """Request body for the RAG query endpoint."""

    question: str = Field(..., min_length=1, max_length=2000)
    model_name: str = Field(
        default_factory=lambda: settings.MODEL_A_NAME,
        description="Name of the model to use for generation.",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve.")


class QueryResponse(BaseModel):
    """Response from the RAG query endpoint."""

    answer: str
    model: str
    sources: list[SourceChunk]
    usage: UsageInfo | None = None
    low_confidence: bool = False
    safety_filtered: bool = False
