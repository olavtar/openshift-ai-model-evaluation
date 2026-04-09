# This project was developed with assistance from AI tools.
"""RAG query endpoint -- retrieve context and generate an answer."""

import logging

from db import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..schemas.query import QueryRequest, QueryResponse, SourceChunk, UsageInfo
from ..services.generation import generate_answer
from ..services.retrieval import retrieve_chunks

logger = logging.getLogger(__name__)
router = APIRouter()

CONFIDENCE_THRESHOLD = 0.5


@router.post("/", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Ask a question against the RAG knowledge base.

    1. Retrieves the top-k most relevant chunks via vector similarity.
    2. Sends the chunks as context to the specified LLM.
    3. Returns the generated answer with source citations.
    """
    if not settings.any_token_configured:
        raise HTTPException(
            status_code=400,
            detail="No API token configured. Set API_TOKEN in your environment.",
        )

    # Validate model_name
    valid_models = [settings.MODEL_A_NAME, settings.MODEL_B_NAME]
    if request.model_name not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model name. Available: {settings.MODEL_A_NAME}, {settings.MODEL_B_NAME}",
        )

    chunks = await retrieve_chunks(
        query=request.question,
        session=session,
        top_k=request.top_k,
    )

    result = await generate_answer(
        question=request.question,
        chunks=chunks,
        model_name=request.model_name,
    )

    sources = [
        SourceChunk(
            id=c["id"],
            text=c["text"],
            source_document=c["source_document"],
            page_number=c.get("page_number"),
            score=c["score"],
        )
        for c in chunks
    ]

    usage = None
    if result.get("usage"):
        usage = UsageInfo(**result["usage"])

    low_confidence = (
        len(sources) > 0 and all(s.score < CONFIDENCE_THRESHOLD for s in sources)
    )

    return QueryResponse(
        answer=result["answer"],
        model=result["model"],
        sources=sources,
        usage=usage,
        low_confidence=low_confidence,
    )
