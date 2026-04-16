# This project was developed with assistance from AI tools.
"""Embedding service -- calls the MaaS /v1/embeddings endpoint."""

import asyncio
import logging
from dataclasses import dataclass

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingsResult:
    """Outcome of embedding generation."""

    vectors: list[list[float] | None] | None
    """Embedding vectors in input order. Individual entries may be None for
    batches that failed. The entire list is None when generation was skipped
    or every batch failed."""

    error: str | None = None
    """Short reason for UI or logs when ``vectors`` is None or partial."""


EMBEDDING_TIMEOUT = 60.0  # seconds
BATCH_SIZE = 16  # chunks per request; each chunk is pre-truncated to ~150 words
RATE_LIMIT_RETRIES = 5
RATE_LIMIT_BACKOFF = 2.0  # seconds; doubles each retry

# Nomic-embed-text (and similar) caps inputs at 512 tokens. Word counts alone are unsafe:
# technical text often exceeds ~2 tokens/word; PDFs can yield huge single "words" with no spaces.
MAX_EMBED_WORDS = 150
MAX_EMBED_CHARS = 1800


def _truncate(text: str) -> str:
    """Truncate text to stay within the embedding model's token limit."""
    t = text.strip()
    if len(t) > MAX_EMBED_CHARS:
        t = t[:MAX_EMBED_CHARS]
    words = t.split()
    if len(words) > MAX_EMBED_WORDS:
        return " ".join(words[:MAX_EMBED_WORDS])
    return t


async def generate_embeddings(texts: list[str]) -> EmbeddingsResult:
    """Generate embeddings for texts via the MaaS endpoint.

    Truncates long texts and sends in batches to avoid token and
    request size limits. On failure, ``vectors`` is None and ``error`` explains why.
    """
    if not settings.API_TOKEN:
        msg = (
            "API_TOKEN is not set on the API server. Set it (or redeploy the secret) "
            "to enable embeddings."
        )
        logger.info("No API token configured -- skipping embeddings")
        return EmbeddingsResult(vectors=None, error=msg)

    if not settings.MAAS_ENDPOINT:
        msg = "MAAS_ENDPOINT is not set on the API server."
        logger.error(msg)
        return EmbeddingsResult(vectors=None, error=msg)

    if not settings.EMBEDDING_MODEL:
        msg = "EMBEDDING_MODEL is not set on the API server."
        logger.error(msg)
        return EmbeddingsResult(vectors=None, error=msg)

    base = settings.MAAS_ENDPOINT.rstrip("/")
    url = f"{base}/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.api_token_bare}",
        "Content-Type": "application/json",
    }

    truncated = [_truncate(t) for t in texts]
    logger.info(
        "Embedding %d texts (max words after truncation: %d, max chars: %d)",
        len(truncated),
        max(len(t.split()) for t in truncated) if truncated else 0,
        max(len(t) for t in truncated) if truncated else 0,
    )
    all_embeddings: list[list[float] | None] = []
    total_batches = (len(truncated) + BATCH_SIZE - 1) // BATCH_SIZE
    failed_batches = 0
    last_error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
            for i in range(0, len(truncated), BATCH_SIZE):
                batch = truncated[i : i + BATCH_SIZE]
                batch_num = i // BATCH_SIZE + 1
                payload = {
                    "model": settings.EMBEDDING_MODEL,
                    "input": batch,
                    "encoding_format": "float",
                }

                try:
                    # Retry loop for rate limiting (429)
                    backoff = RATE_LIMIT_BACKOFF
                    for attempt in range(RATE_LIMIT_RETRIES + 1):
                        response = await client.post(url, json=payload, headers=headers)
                        if response.status_code == 429 and attempt < RATE_LIMIT_RETRIES:
                            logger.warning(
                                "Embedding rate limited (batch %d/%d), retrying in %.1fs",
                                batch_num,
                                total_batches,
                                backoff,
                            )
                            await asyncio.sleep(backoff)
                            backoff *= 2
                            continue
                        response.raise_for_status()
                        break

                    data = response.json()
                    all_embeddings.extend(item["embedding"] for item in data["data"])
                except Exception as batch_err:
                    failed_batches += 1
                    last_error = f"Batch {batch_num}/{total_batches} failed: {batch_err!s}"[:300]
                    logger.error(
                        "Embedding batch %d/%d failed: %s", batch_num, total_batches, batch_err
                    )
                    all_embeddings.extend(None for _ in batch)

    except Exception as e:
        logger.error("Embedding client setup failed: %s", e)
        return EmbeddingsResult(vectors=None, error=f"Embedding request failed: {e!s}"[:500])

    if failed_batches == total_batches:
        return EmbeddingsResult(vectors=None, error=last_error)

    error_msg = None
    if failed_batches > 0:
        error_msg = f"{failed_batches}/{total_batches} batches failed; {last_error}"
        logger.warning("Partial embedding: %s", error_msg)

    return EmbeddingsResult(vectors=all_embeddings, error=error_msg)
