# This project was developed with assistance from AI tools.
"""Truth generation service -- creates structured truth payloads for questions.

Generates truth for two entry paths:
- Synthesis: concepts extracted from expected answer, retrieval truth traced from
  the chunks used during question generation.
- Manual: concepts extracted from expected answer, retrieval truth grounded by
  running the expected answer through the same retrieval pipeline as evaluation.
"""

import json
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..schemas.truth import AnswerTruth, RetrievalTruth, TruthMetadata, TruthPayload
from .coverage import COVERAGE_TIMEOUT, EXTRACT_CONCEPTS_PROMPT, _strip_markdown_fencing
from .retrieval import retrieve_chunks

logger = logging.getLogger(__name__)


async def extract_answer_truth(expected_answer: str, model_name: str) -> AnswerTruth:
    """Extract required concepts from an expected answer using the judge model.

    Reuses the same concept extraction prompt as coverage.py to ensure
    consistent concept definitions.

    Args:
        expected_answer: The ground truth answer text.
        model_name: Model to use for concept extraction.

    Returns:
        AnswerTruth with extracted concepts.

    Raises:
        RuntimeError: If concept extraction fails.
    """
    model_cfg = settings.get_model_config(model_name)
    if not model_cfg["token"]:
        raise RuntimeError("No API token configured for truth generation.")

    url = f"{model_cfg['endpoint']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": EXTRACT_CONCEPTS_PROMPT.format(expected_answer=expected_answer),
            },
        ],
        "temperature": 0.0,
        "max_tokens": 512,
    }

    try:
        async with httpx.AsyncClient(timeout=COVERAGE_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        content = _strip_markdown_fencing(content)

        concepts = json.loads(content)
        if not isinstance(concepts, list) or not concepts:
            raise RuntimeError("Concept extraction returned empty or non-list result")

        required_concepts = [c.strip() for c in concepts if isinstance(c, str) and c.strip()]
        if not required_concepts:
            raise RuntimeError("No valid concepts extracted from expected answer")

        logger.info("Truth generation: extracted %d concepts", len(required_concepts))
        return AnswerTruth(required_concepts=required_concepts)

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse concept extraction response: {e}") from e
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Concept extraction HTTP {e.response.status_code}") from e


def build_retrieval_truth_from_synthesis(source_chunks: list[dict]) -> RetrievalTruth:
    """Build retrieval truth from chunks used during question synthesis.

    Args:
        source_chunks: Chunk dicts with 'id' and 'source_document' keys.

    Returns:
        RetrievalTruth with traced evidence.
    """
    required_documents = sorted(
        {c["source_document"] for c in source_chunks if c.get("source_document")}
    )
    expected_chunk_refs = [f"chunk:{c['id']}" for c in source_chunks if c.get("id")]

    return RetrievalTruth(
        required_documents=required_documents,
        expected_chunk_refs=expected_chunk_refs,
        evidence_mode="traced_from_synthesis",
    )


async def ground_answer_to_corpus(
    expected_answer: str,
    session: AsyncSession,
    retrieval_kwargs: dict | None = None,
) -> RetrievalTruth:
    """Ground an expected answer against the uploaded corpus.

    Uses the same retrieval pipeline as evaluation to find chunks that
    best match the expected answer text.

    Args:
        expected_answer: The expected answer text to ground.
        session: Database session for retrieval queries.
        retrieval_kwargs: Profile-driven retrieval parameters (top_k, etc.).

    Returns:
        RetrievalTruth with corpus-grounded evidence.
    """
    kwargs = retrieval_kwargs or {}
    chunks = await retrieve_chunks(
        query=expected_answer,
        session=session,
        **kwargs,
    )

    required_documents = sorted({c["source_document"] for c in chunks if c.get("source_document")})
    expected_chunk_refs = [f"chunk:{c['id']}" for c in chunks if c.get("id")]
    source_chunk_ids = [c["id"] for c in chunks if c.get("id")]

    logger.info(
        "Corpus grounding: %d chunks from %d documents",
        len(chunks),
        len(required_documents),
    )

    return RetrievalTruth(
        required_documents=required_documents,
        expected_chunk_refs=expected_chunk_refs,
        evidence_mode="grounded_from_manual_answer",
    ), source_chunk_ids


def build_truth_metadata(model_name: str, source_chunk_ids: list[int]) -> TruthMetadata:
    """Build truth metadata with version fields and provenance.

    Args:
        model_name: Model used for concept extraction.
        source_chunk_ids: IDs of chunks that informed this truth.

    Returns:
        TruthMetadata with current timestamp and version fields.
    """
    return TruthMetadata(
        generated_by_model=model_name,
        generated_at=datetime.now(UTC).replace(tzinfo=None),
        source_chunk_ids=source_chunk_ids,
    )


async def generate_truth_from_synthesis(
    expected_answer: str,
    source_chunks: list[dict],
    model_name: str,
) -> TruthPayload:
    """Generate a complete truth payload for a synthesized question.

    Args:
        expected_answer: LLM-generated expected answer.
        source_chunks: Chunks used during synthesis, each with 'id' and
            'source_document' keys.
        model_name: Judge model for concept extraction.

    Returns:
        Complete TruthPayload with traced retrieval truth.
    """
    answer_truth = await extract_answer_truth(expected_answer, model_name)
    retrieval_truth = build_retrieval_truth_from_synthesis(source_chunks)
    source_chunk_ids = [c["id"] for c in source_chunks if c.get("id")]
    metadata = build_truth_metadata(model_name, source_chunk_ids)

    return TruthPayload(
        answer_truth=answer_truth,
        retrieval_truth=retrieval_truth,
        metadata=metadata,
    )


async def generate_truth_from_manual_answer(
    expected_answer: str,
    session: AsyncSession,
    model_name: str,
    retrieval_kwargs: dict | None = None,
) -> TruthPayload:
    """Generate a complete truth payload for a manual question with expected answer.

    Grounds the expected answer against the uploaded corpus using the same
    retrieval pipeline as evaluation.

    Args:
        expected_answer: User-provided expected answer.
        session: Database session for corpus retrieval.
        model_name: Judge model for concept extraction.
        retrieval_kwargs: Profile-driven retrieval parameters.

    Returns:
        Complete TruthPayload with corpus-grounded retrieval truth.
    """
    answer_truth = await extract_answer_truth(expected_answer, model_name)
    retrieval_truth, source_chunk_ids = await ground_answer_to_corpus(
        expected_answer, session, retrieval_kwargs
    )
    metadata = build_truth_metadata(model_name, source_chunk_ids)

    return TruthPayload(
        answer_truth=answer_truth,
        retrieval_truth=retrieval_truth,
        metadata=metadata,
    )
