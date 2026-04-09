# This project was developed with assistance from AI tools.
"""Retrieval service -- hybrid search with vector similarity and keyword matching.

Supports profile-driven configuration: top_k, max_chunks_per_document,
rerank_depth, document_diversity_min, and keyword_search_enabled.
Merges vector and keyword results via Reciprocal Rank Fusion (RRF).
"""

import logging
from collections import defaultdict

from db import Chunk, Document
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .embedding import generate_embeddings

logger = logging.getLogger(__name__)

TOP_K = 5  # default number of chunks to retrieve


async def retrieve_chunks(
    query: str,
    session: AsyncSession,
    top_k: int = TOP_K,
    max_per_doc: int | None = None,
    rerank_depth: int = 20,
    diversity_min: int = 3,
    keyword_enabled: bool = True,
) -> list[dict]:
    """Retrieve the most relevant chunks for a query.

    Uses hybrid retrieval when keyword search is enabled: vector similarity
    and PostgreSQL full-text search merged via Reciprocal Rank Fusion (RRF).
    Falls back to recent chunks if embeddings are unavailable.

    Args:
        query: The search query.
        session: Database session.
        top_k: Number of chunks to return.
        max_per_doc: Max chunks per source document (None = unlimited).
        rerank_depth: Number of RRF candidates to consider before selecting top_k.
        diversity_min: Soft target for minimum number of distinct source documents.
        keyword_enabled: Whether to include keyword search in hybrid retrieval.

    Returns:
        List of dicts with 'id', 'text', 'source_document', 'page_number',
        'section_path', 'score' keys, ordered by relevance.
    """
    result = await generate_embeddings([query])

    if result.vectors:
        vector_results = await _vector_search(result.vectors[0], session, rerank_depth)
    else:
        logger.info("No query embedding available -- falling back to recent chunks")
        if result.error:
            logger.info("Embedding issue: %s", result.error)
        return await _fallback_search(session, top_k)

    # Keyword search (graceful degradation: returns [] if not supported)
    keyword_results = []
    if keyword_enabled:
        keyword_results = await _keyword_search(query, session, rerank_depth)

    # Merge via RRF
    if keyword_results:
        merged = _reciprocal_rank_fusion(vector_results, keyword_results)
    else:
        merged = vector_results

    # Apply document diversity and per-doc caps
    final = _apply_diversity(merged, top_k, max_per_doc, diversity_min)

    return final


async def _vector_search(
    query_embedding: list[float],
    session: AsyncSession,
    limit: int,
) -> list[dict]:
    """Search chunks by cosine similarity to the query embedding."""
    dist = Chunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(
            Chunk.id,
            Chunk.text,
            Chunk.source_document,
            Chunk.page_number,
            Chunk.section_path,
            (1 - dist).label("score"),
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.embedding.isnot(None), Document.deleted_at.is_(None))
        .order_by(dist)
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": row.id,
            "text": row.text,
            "source_document": row.source_document,
            "page_number": row.page_number,
            "section_path": row.section_path,
            "score": round(float(row.score), 4),
        }
        for row in rows
    ]


async def _keyword_search(
    query: str,
    session: AsyncSession,
    limit: int,
) -> list[dict]:
    """Search chunks using PostgreSQL full-text search.

    Returns empty list gracefully if full-text search is not available
    (e.g., SQLite in tests).
    """
    try:
        ts_query = func.plainto_tsquery("english", query)
        ts_vector = func.to_tsvector("english", Chunk.text)
        rank = func.ts_rank(ts_vector, ts_query)

        stmt = (
            select(
                Chunk.id,
                Chunk.text,
                Chunk.source_document,
                Chunk.page_number,
                Chunk.section_path,
                rank.label("score"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(ts_vector.bool_op("@@")(ts_query), Document.deleted_at.is_(None))
            .order_by(rank.desc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "text": row.text,
                "source_document": row.source_document,
                "page_number": row.page_number,
                "section_path": row.section_path,
                "score": round(float(row.score), 4),
            }
            for row in rows
        ]
    except Exception:
        # Graceful fallback for SQLite or unsupported databases
        logger.debug("Keyword search not available, skipping")
        return []


def _reciprocal_rank_fusion(
    *result_lists: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) across all lists.

    Args:
        result_lists: Multiple ranked lists of chunk dicts.
        k: RRF constant (default 60, standard value from the RRF paper).

    Returns:
        Merged list sorted by combined RRF score.
    """
    rrf_scores: dict[int, float] = defaultdict(float)
    chunk_map: dict[int, dict] = {}

    for results in result_lists:
        for rank, chunk in enumerate(results):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] += 1.0 / (k + rank + 1)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = chunk

    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    return [
        {**chunk_map[cid], "score": round(rrf_scores[cid], 4)}
        for cid in sorted_ids
    ]


def _apply_diversity(
    chunks: list[dict],
    top_k: int,
    max_per_doc: int | None,
    diversity_min: int,
) -> list[dict]:
    """Apply document diversity and per-document caps.

    Strategy:
    1. If max_per_doc is set, cap chunks per source document.
    2. If we have fewer than diversity_min documents, promote underrepresented
       docs from lower-ranked positions.
    3. Return top_k results.

    Args:
        chunks: Ranked list of chunks (already sorted by relevance/RRF).
        top_k: Number of chunks to return.
        max_per_doc: Max chunks per document (None = unlimited).
        diversity_min: Soft target for document diversity.

    Returns:
        Filtered list of up to top_k chunks.
    """
    if not chunks:
        return []

    # Apply per-document cap
    if max_per_doc:
        doc_counts: dict[str, int] = defaultdict(int)
        capped: list[dict] = []
        deferred: list[dict] = []
        for chunk in chunks:
            doc = chunk["source_document"]
            if doc_counts[doc] < max_per_doc:
                capped.append(chunk)
                doc_counts[doc] += 1
            else:
                deferred.append(chunk)
        chunks = capped + deferred

    # Diversity promotion: ensure at least diversity_min distinct documents
    if diversity_min > 1 and len(chunks) > top_k:
        selected: list[dict] = []
        remaining: list[dict] = list(chunks)
        seen_docs: set[str] = set()

        # First pass: pick one from each unseen document until diversity_min
        for chunk in list(remaining):
            if len(seen_docs) >= diversity_min:
                break
            if chunk["source_document"] not in seen_docs:
                selected.append(chunk)
                remaining.remove(chunk)
                seen_docs.add(chunk["source_document"])

        # Fill rest by rank order
        for chunk in remaining:
            if len(selected) >= top_k:
                break
            selected.append(chunk)

        return selected[:top_k]

    return chunks[:top_k]


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
            Chunk.section_path,
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
            "section_path": getattr(row, "section_path", None),
            "score": 0.0,
        }
        for row in rows
    ]
