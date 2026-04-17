# This project was developed with assistance from AI tools.
"""Generation service -- calls the LLM via the MaaS /v1/chat/completions endpoint."""

import logging

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

GENERATION_TIMEOUT = 120.0  # seconds
_DEBUG_ERROR_SNIPPET_LEN = 500


def _summarize_upstream_error(response: httpx.Response) -> str:
    """Best-effort extract a short message from an OpenAI-style error body."""
    text = (response.text or "").strip()
    try:
        data = response.json()
    except Exception:
        return text[:_DEBUG_ERROR_SNIPPET_LEN] + (
            "..." if len(text) > _DEBUG_ERROR_SNIPPET_LEN else ""
        )

    err = data.get("error")
    if isinstance(err, dict):
        for key in ("message", "detail", "msg"):
            val = err.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:_DEBUG_ERROR_SNIPPET_LEN]
    if isinstance(err, str) and err.strip():
        return err.strip()[:_DEBUG_ERROR_SNIPPET_LEN]

    detail = data.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()[:_DEBUG_ERROR_SNIPPET_LEN]

    return text[:_DEBUG_ERROR_SNIPPET_LEN] + ("..." if len(text) > _DEBUG_ERROR_SNIPPET_LEN else "")


SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based on the provided context. "
    "Use only the information from the context to answer. If the context does not contain "
    "enough information to answer the question, say so clearly.\n\n"
    "SYNTHESIS REQUIREMENTS:\n"
    "- Organize your answer by topic, not by source document. Group related information "
    "from different sources under the same topic heading.\n"
    "- Synthesize across all RELEVANT documents in the context. Do not include documents "
    "that do not contribute meaningful information.\n"
    "- For each major point, cite the source document name and page number when available.\n"
    "- Cover as many distinct topics as the context supports rather than focusing deeply "
    "on just one area.\n"
    "- Do not fabricate connections between documents that are not supported by the context."
)


def _build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for the prompt."""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk["source_document"]
        page = chunk.get("page_number")
        header = f"[Source {i}: {source}"
        if page:
            header += f", page {page}"
        header += "]"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n".join(parts)


async def generate_answer(
    question: str,
    chunks: list[dict],
    model_name: str,
    system_prompt: str | None = None,
) -> dict:
    """Generate an answer using the specified model with retrieved context.

    Args:
        question: The user's question.
        chunks: Retrieved context chunks from the retrieval service.
        model_name: Name of the model to use (e.g. granite-3.1-8b-instruct).
        system_prompt: Optional override for the system prompt. When provided
            (e.g. from an evaluation profile), replaces the default prompt.

    Returns:
        Dict with 'answer', 'model', 'usage' keys.
    """
    model_cfg = settings.get_model_config(model_name)
    if not model_cfg["token"]:
        return {
            "answer": f"No API token configured for model {model_name}.",
            "model": model_name,
            "usage": None,
        }

    context = _build_context_block(chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {question}"

    url = f"{model_cfg['endpoint']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=GENERATION_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

        return {
            "answer": answer,
            "model": model_name,
            "usage": usage,
        }

    except httpx.HTTPStatusError as e:
        detail = _summarize_upstream_error(e.response)
        logger.error(
            "Generation API HTTP %s for model %r: %s",
            e.response.status_code,
            model_name,
            detail or "(empty body)",
        )
        msg = f"Model {model_name} returned an error: {e.response.status_code}"
        if settings.DEBUG and detail:
            msg = f"{msg}. {detail}"
        return {
            "answer": msg,
            "model": model_name,
            "usage": None,
        }
    except Exception as e:
        logger.error("Generation request failed: %s", e)
        return {
            "answer": f"Failed to generate answer: {e}",
            "model": model_name,
            "usage": None,
        }
