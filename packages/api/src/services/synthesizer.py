# This project was developed with assistance from AI tools.
"""Question synthesizer -- generates evaluation questions from document chunks."""

import json
import logging

import httpx
from db import Chunk, Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from .generation import GENERATION_TIMEOUT, _summarize_upstream_error

logger = logging.getLogger(__name__)

MAX_CONTEXTS = 50


_SYNTHESIZE_PROMPT = """\
You are given excerpts from regulatory and compliance documents. \
Generate exactly {count} question-and-answer pairs that can ONLY be answered \
using the information in the excerpts below. Do NOT invent facts or use outside knowledge.

Rules:
- Each question must be answerable from the provided text.
- Each answer must quote or closely paraphrase the source text.
- Focus on specific regulatory requirements, obligations, thresholds, and definitions.

Respond in JSON: {{"questions": [{{"question": "...", "expected_answer": "..."}}]}}

--- DOCUMENT EXCERPTS ---
{context}
--- END EXCERPTS ---"""


def _parse_questions_json(raw: str) -> dict:
    """Parse model JSON; tolerate optional ```json fences."""
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


async def generate_questions(
    session: AsyncSession,
    document_ids: list[int] | None = None,
    max_questions: int = 10,
) -> list[dict]:
    """Generate evaluation questions from ingested document chunks.

    Calls the same OpenAI-compatible chat endpoint as RAG generation (httpx),
    using ``question_synthesis_model_name`` (see Settings).

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

    model_name = settings.question_synthesis_model_name
    if not model_name:
        raise RuntimeError(
            "No model configured for question synthesis. Set MODEL_A_NAME, JUDGE_MODEL_NAME, "
            "or QUESTION_SYNTHESIS_MODEL_NAME."
        )

    model_cfg = settings.get_model_config(model_name)
    if not model_cfg["token"]:
        raise RuntimeError("No API token configured for question synthesis.")

    context = "\n\n".join(chunk_texts[:MAX_CONTEXTS])
    prompt = _SYNTHESIZE_PROMPT.format(count=max_questions, context=context)

    url = f"{model_cfg['endpoint']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    try:
        async with httpx.AsyncClient(timeout=GENERATION_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        text = data["choices"][0]["message"]["content"]
        parsed = _parse_questions_json(text)

        raw_questions = parsed.get("questions", [])
        questions = []
        for item in raw_questions[:max_questions]:
            if isinstance(item, dict) and item.get("question"):
                questions.append({
                    "question": item["question"],
                    "expected_answer": item.get("expected_answer"),
                })

        return questions

    except httpx.HTTPStatusError as e:
        detail = _summarize_upstream_error(e.response)
        logger.error(
            "Question synthesis HTTP %s for model %r: %s",
            e.response.status_code,
            model_name,
            detail or "(empty body)",
        )
        raise RuntimeError(detail or f"Model returned HTTP {e.response.status_code}") from e
    except Exception as e:
        logger.error("Question synthesis failed: %s", e, exc_info=True)
        raise
