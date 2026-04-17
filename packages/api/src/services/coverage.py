# This project was developed with assistance from AI tools.
"""Coverage gap detection -- extracts key concepts from expected answers
and checks which are present in the model's actual answer.

Uses the judge LLM to:
1. Extract required concepts from the expected answer (Step 4)
2. Check which concepts the actual answer covers (Step 5)

Returns a structured report of covered vs missing concepts, explaining
WHY completeness is low rather than just reporting the score.
"""

import json
import logging

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

COVERAGE_TIMEOUT = 60.0  # seconds


EXTRACT_AND_CHECK_PROMPT = """\
You are an evaluation analyst for regulatory document Q&A.

Given an EXPECTED ANSWER and an ACTUAL ANSWER, do two things:

1. Extract the key concepts, requirements, or facts from the EXPECTED ANSWER.
   Each concept should be a short phrase (5-15 words) that captures one distinct
   piece of information.

2. For each concept, determine if the ACTUAL ANSWER covers it:
   - "covered" = the concept is present or adequately addressed
   - "missing" = the concept is absent or not addressed

Respond with a JSON object:
{{
  "concepts": [
    {{"text": "concept description", "status": "covered"}},
    {{"text": "concept description", "status": "missing"}}
  ]
}}

No other text. Just the JSON object.

EXPECTED ANSWER:
{expected_answer}

ACTUAL ANSWER:
{actual_answer}
"""


async def detect_coverage_gaps(
    expected_answer: str,
    actual_answer: str,
    model_name: str | None = None,
) -> dict | None:
    """Extract key concepts from expected answer and check coverage.

    Args:
        expected_answer: The ground truth answer.
        actual_answer: The model's generated answer.
        model_name: Model to use for analysis. Defaults to the judge model.

    Returns:
        Dict with 'concepts', 'covered', 'missing', 'coverage_ratio' keys,
        or None if analysis fails.
    """
    resolved_model = model_name or settings.resolved_judge_model_name
    if not resolved_model:
        logger.info("No model configured for coverage analysis, skipping")
        return None

    model_cfg = settings.get_model_config(resolved_model)
    if not model_cfg["token"]:
        logger.info("No API token for coverage model, skipping")
        return None

    url = f"{model_cfg['endpoint']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "user",
                "content": EXTRACT_AND_CHECK_PROMPT.format(
                    expected_answer=expected_answer,
                    actual_answer=actual_answer,
                ),
            },
        ],
        "temperature": 0.0,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=COVERAGE_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fencing if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            content = "\n".join(lines).strip()

        parsed = json.loads(content)
        concepts = parsed.get("concepts", [])
        if not isinstance(concepts, list) or not concepts:
            logger.warning("Coverage analysis returned empty concepts")
            return None

        covered = [c["text"] for c in concepts if c.get("status") == "covered"]
        missing = [c["text"] for c in concepts if c.get("status") == "missing"]
        all_texts = [c["text"] for c in concepts]

        result = {
            "concepts": all_texts,
            "covered": covered,
            "missing": missing,
            "coverage_ratio": len(covered) / len(all_texts) if all_texts else 1.0,
        }

        logger.info(
            "Coverage analysis: %d/%d concepts covered (%.0f%%), missing: %s",
            len(covered),
            len(all_texts),
            result["coverage_ratio"] * 100,
            missing[:5] if missing else "none",
        )

        return result

    except json.JSONDecodeError:
        logger.warning("Failed to parse coverage analysis response as JSON")
        return None
    except Exception as e:
        logger.warning("Coverage analysis failed (%s), skipping", e)
        return None
