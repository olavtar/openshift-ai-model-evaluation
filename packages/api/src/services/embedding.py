# This project was developed with assistance from AI tools.
"""Embedding service -- calls the MaaS /v1/embeddings endpoint."""

import logging

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_TIMEOUT = 60.0  # seconds


async def generate_embeddings(texts: list[str]) -> list[list[float]] | None:
    """Generate embeddings for a batch of texts via the MaaS endpoint.

    Returns None if embedding is unavailable (no API token configured
    or endpoint error), allowing the upload to succeed without embeddings.
    Embeddings can be backfilled later.
    """
    if not settings.embedding_token:
        logger.info("No API token configured for embedding model -- skipping embeddings")
        return None

    url = f"{settings.embedding_endpoint}/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.embedding_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": texts,
    }

    try:
        async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        # OpenAI-compatible response: {"data": [{"embedding": [...], "index": 0}, ...]}
        embeddings = [item["embedding"] for item in data["data"]]
        return embeddings

    except httpx.HTTPStatusError as e:
        logger.error("Embedding API returned status %s", e.response.status_code)
        return None
    except Exception as e:
        logger.error("Embedding request failed: %s", e)
        return None
