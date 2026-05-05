# This project was developed with assistance from AI tools.
"""Query decomposition service -- breaks broad questions into targeted sub-queries.

For multi-document RAG, a single broad question tends to retrieve chunks from
the most semantically dominant document. Decomposing into sub-queries that each
target a distinct regulatory concept or document type forces retrieval to span
multiple documents, improving completeness.
"""

import json
import logging
import re

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

DECOMPOSITION_TIMEOUT = 30.0  # seconds

# In-memory cache for decomposition results (avoids re-calling LLM for the
# same question across model A and model B eval runs, or rerun scenarios).
_decomposition_cache: dict[str, list[str]] = {}
_CACHE_MAX_SIZE = 200


def _get_cached_decomposition(question: str) -> list[str] | None:
    return _decomposition_cache.get(question)


def _cache_decomposition(question: str, sub_queries: list[str]) -> None:
    if len(_decomposition_cache) >= _CACHE_MAX_SIZE:
        # Evict oldest entry
        oldest = next(iter(_decomposition_cache))
        del _decomposition_cache[oldest]
    _decomposition_cache[question] = sub_queries
MAX_SUB_QUERIES = 7

# Words per question below which decomposition is skipped (narrow questions)
_MIN_WORDS_FOR_DECOMPOSITION = 8

# Broad-question signal words that suggest decomposition would help
_BROAD_SIGNALS = {
    "key", "main", "overview", "requirements", "framework", "comprehensive",
    "summary", "compare", "differences", "explain", "describe", "what are",
    "how do", "regulatory", "compliance", "obligations", "all", "various",
    "multiple", "different", "types", "categories",
}

DECOMPOSITION_PROMPT = """\
You are a query decomposition assistant for a regulatory document retrieval system.

Given a broad question, break it into {max_sub_queries} specific sub-questions that:
1. Each target a DISTINCT regulatory concept, document type, or compliance area
2. Avoid overlapping semantic intent -- each sub-question should retrieve from \
a different part of the document corpus
3. Together cover the full scope of the original question
4. Are self-contained (each can be understood without the others)

Respond with a JSON array of strings. No other text.

Example:
Question: "What are the key requirements for ETF regulatory compliance?"
Output: ["What registration and prospectus requirements apply to ETFs under Form N-1A?", \
"What disclosures are required in an ETF's Statement of Additional Information (SAI)?", \
"How do creation and redemption mechanisms work for ETFs, including authorized participants and creation units?", \
"What periodic reporting requirements apply to ETFs under Forms N-CSR, N-PORT, and N-CEN?", \
"What are the provisions of Rule 6c-11 regarding ETF transparency and website disclosures?", \
"What are the requirements for ETF net asset value (NAV) calculation and portfolio holdings disclosure?", \
"What premium/discount and bid-ask spread disclosure requirements apply to ETFs?"]
"""


async def decompose_query(
    question: str,
    model_name: str | None = None,
    max_sub_queries: int = MAX_SUB_QUERIES,
) -> list[str]:
    """Decompose a broad question into targeted sub-queries.

    Uses an LLM to break the question into sub-queries that each target
    a distinct concept. Falls back to returning the original question
    if decomposition fails.

    Args:
        question: The broad question to decompose.
        model_name: Model to use for decomposition. Defaults to the
            judge model or first available chat model.
        max_sub_queries: Maximum number of sub-queries to generate.

    Returns:
        List of sub-query strings. Returns [question] on failure.
    """
    # Check cache first
    cached = _get_cached_decomposition(question)
    if cached is not None:
        logger.info("Using cached decomposition for: %.60s", question)
        return cached[:max_sub_queries]

    # Cheap gate: skip decomposition for narrow, single-concept questions
    words = question.split()
    if len(words) < _MIN_WORDS_FOR_DECOMPOSITION:
        logger.info("Question too short for decomposition (%d words), using original", len(words))
        return [question]

    question_lower = question.lower()
    has_broad_signal = any(signal in question_lower for signal in _BROAD_SIGNALS)
    if not has_broad_signal:
        logger.info("No broad-question signals detected, skipping decomposition")
        return [question]

    resolved_model = model_name or settings.resolved_judge_model_name
    if not resolved_model:
        logger.info("No model configured for query decomposition, using original query")
        return [question]

    model_cfg = settings.get_model_config(resolved_model)
    if not model_cfg["token"]:
        logger.info("No API token for decomposition model, using original query")
        return [question]

    url = f"{model_cfg['endpoint']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "system",
                "content": DECOMPOSITION_PROMPT.format(max_sub_queries=max_sub_queries),
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.0,
        "max_tokens": 512,
    }

    try:
        async with httpx.AsyncClient(timeout=DECOMPOSITION_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        sub_queries = _parse_decomposition_json(content)
        if not sub_queries:
            logger.warning("Decomposition returned empty result, using original query")
            return [question]

        # Validate and clean
        result = [q.strip() for q in sub_queries if isinstance(q, str) and q.strip()]
        if not result:
            return [question]

        truncated = result[:max_sub_queries]
        _cache_decomposition(question, truncated)
        logger.info(
            "Decomposed query into %d sub-queries: %s",
            len(truncated),
            [q[:60] + "..." if len(q) > 60 else q for q in truncated],
        )
        return truncated

    except Exception as e:
        logger.warning("Query decomposition failed (%s), using original query", e)
        return [question]


def _parse_decomposition_json(raw: str) -> list[str] | None:
    """Parse decomposition response with fallbacks for malformed JSON."""
    text = raw.strip()

    # Strip markdown fencing
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # Repair trailing/missing commas
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    repaired = re.sub(r'"\s*\n(\s*")', r'",\n\1', repaired)
    try:
        parsed = json.loads(repaired)
        if isinstance(parsed, list) and parsed:
            logger.info("Decomposition JSON parsed after repair")
            return parsed
    except json.JSONDecodeError:
        pass

    # Last resort: extract quoted strings
    strings = re.findall(r'"((?:[^"\\]|\\.)+)"', text)
    if strings:
        logger.warning(
            "Decomposition JSON parse failed, extracted %d strings via regex", len(strings)
        )
        return strings

    logger.warning("Failed to parse decomposition response as JSON")
    return None
