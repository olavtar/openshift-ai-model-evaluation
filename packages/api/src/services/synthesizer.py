# This project was developed with assistance from AI tools.
"""Question synthesizer using DeepEval to auto-generate evaluation questions from documents."""

import logging

from db import Chunk, Document
from deepeval.synthesizer import Synthesizer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from .scoring import MaaSJudgeModel

logger = logging.getLogger(__name__)

MAX_CONTEXTS = 50


async def generate_questions(
    session: AsyncSession,
    document_ids: list[int] | None = None,
    max_questions: int = 10,
) -> list[dict]:
    """Generate evaluation questions from ingested document chunks.

    Uses DeepEval's Synthesizer with the MaaS judge model to create
    question/expected-answer pairs from existing document chunks.

    Args:
        session: Database session.
        document_ids: Optional list of document IDs to filter chunks.
            If None, uses chunks from all ready documents.
        max_questions: Maximum number of questions to generate.

    Returns:
        List of dicts with 'question' and 'expected_answer' keys.
    """
    query = (
        select(Chunk.text)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.status == "ready", Document.deleted_at.is_(None))
    )
    if document_ids:
        query = query.where(Chunk.document_id.in_(document_ids))

    query = query.order_by(Chunk.id).limit(MAX_CONTEXTS)

    result = await session.execute(query)
    chunk_texts = [row[0] for row in result.all()]

    if not chunk_texts:
        return []

    judge = MaaSJudgeModel(
        model_name=settings.JUDGE_MODEL_NAME,
        base_url=settings.MAAS_ENDPOINT,
        api_key=settings.MODEL_API_TOKEN,
    )

    synthesizer = Synthesizer(model=judge)

    # DeepEval expects contexts as list of list of strings
    # Each inner list is a group of contexts for one question
    # We group chunks in pairs to give the synthesizer richer context
    context_groups = []
    for i in range(0, len(chunk_texts), 2):
        group = chunk_texts[i : i + 2]
        context_groups.append(group)

    if not context_groups:
        return []

    goldens = await synthesizer.a_generate_goldens_from_contexts(
        contexts=context_groups,
        max_goldens_per_context=max(1, max_questions // len(context_groups)),
    )

    questions = []
    for golden in goldens[:max_questions]:
        questions.append({
            "question": golden.input,
            "expected_answer": golden.expected_output,
        })

    return questions
