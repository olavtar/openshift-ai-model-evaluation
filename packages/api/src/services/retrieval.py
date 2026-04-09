# This project was developed with assistance from AI tools.
"""Retrieval service -- vector similarity search against chunk embeddings."""

import logging

from db import Chunk, Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    result = await generate_embeddings([query])

    if result.vectors:
        return await _vector_search(result.vectors[0], session, top_k)

    logger.info("No query embedding available -- falling back to recent chunks")
    if result.error:
        logger.info("Embedding issue: %s", result.error)
    return await _fallback_search(session, top_k)


async def _vector_search(
    query_embedding: list[float],
    session: AsyncSession,
    top_k: int,
) -> list[dict]:
    """Search chunks by cosine similarity to the query embedding."""
    # Pass a Python list so pgvector's bind processor serializes it correctly.
    # A pre-formatted "[...]" string is treated as a single invalid value and
    # raises ValueError inside numpy/pgvector when binding.
    dist = Chunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(
            Chunk.id,
            Chunk.text,
            Chunk.source_document,
            Chunk.page_number,
            (1 - dist).label("score"),
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.embedding.isnot(None), Document.deleted_at.is_(None))
        .order_by(dist)
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
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.deleted_at.is_(None))
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
