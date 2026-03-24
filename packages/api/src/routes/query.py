# This project was developed with assistance from AI tools.
"""RAG query endpoint -- retrieve context and generate an answer."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

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
