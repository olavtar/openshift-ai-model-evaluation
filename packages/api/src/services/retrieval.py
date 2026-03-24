# This project was developed with assistance from AI tools.
"""Retrieval service -- vector similarity search against chunk embeddings."""

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import Chunk, EMBEDDING_DIMENSION

from .embedding import generate_embeddings

logger = logging.getLogger(__name__)

TOP_K = 5  # number of chunks to retrieve


async def retrieve_chunks(
    query: str,
    session: AsyncSession,
    top_k: int = TOP_K,
) -> list[dict]:
    """Retrieve the most relevant chunks for a query using cosine similarity.

    Falls back to returning recent chunks if embeddings are unavailable.

    Returns:
        List of dicts with 'id', 'text', 'source_document', 'page_number',
        'score' keys, ordered by relevance.
    """
    # Generate query embedding
    embeddings = await generate_embeddings([query])

    if embeddings:
        return await _vector_search(embeddings[0], session, top_k)

    logger.info("No query embedding available -- falling back to recent chunks")
    return await _fallback_search(session, top_k)


async def _vector_search(
    query_embedding: list[float],
    session: AsyncSession,
    top_k: int,
) -> list[dict]:
    """Search chunks by cosine similarity to the query embedding."""
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    stmt = (
        select(
            Chunk.id,
            Chunk.text,
            Chunk.source_document,
            Chunk.page_number,
            (1 - Chunk.embedding.cosine_distance(embedding_str)).label("score"),
        )
        .where(Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(embedding_str))
        .limit(top_k)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": row.id,
            "text": row.text,
            "source_document": row.source_document,
            "page_number": row.page_number,
            "score": round(float(row.score), 4),
        }
        for row in rows
    ]


async def _fallback_search(
    session: AsyncSession,
    top_k: int,
) -> list[dict]:
    """Return the most recent chunks when vector search is unavailable."""
    stmt = (
        select(
            Chunk.id,
            Chunk.text,
            Chunk.source_document,
            Chunk.page_number,
        )
        .order_by(Chunk.created_at.desc())
        .limit(top_k)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": row.id,
            "text": row.text,
            "source_document": row.source_document,
            "page_number": row.page_number,
            "score": 0.0,
        }
        for row in rows
    ]
