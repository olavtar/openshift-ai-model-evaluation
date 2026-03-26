# This project was developed with assistance from AI tools.
"""Generation service -- calls the LLM via the MaaS /v1/chat/completions endpoint."""

import logging

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

GENERATION_TIMEOUT = 120.0  # seconds

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based on the provided context. "
    "Use only the information from the context to answer. If the context does not contain "
    "enough information to answer the question, say so clearly. "
    "Cite the source document and page number when available."
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
) -> dict:
    """Generate an answer using the specified model with retrieved context.

    Args:
        question: The user's question.
        chunks: Retrieved context chunks from the retrieval service.
        model_name: Name of the model to use (e.g. granite-3.1-8b-instruct).

    Returns:
        Dict with 'answer', 'model', 'usage' keys.
    """
    if not settings.MODEL_API_TOKEN:
        return {
            "answer": "No MODEL_API_TOKEN configured. Cannot generate answers.",
            "model": model_name,
            "usage": None,
        }

    context = _build_context_block(chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {question}"

    url = f"{settings.MAAS_ENDPOINT}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.MODEL_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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
        logger.error("Generation API returned status %s", e.response.status_code)
        return {
            "answer": f"Model {model_name} returned an error: {e.response.status_code}",
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
