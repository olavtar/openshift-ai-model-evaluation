# This project was developed with assistance from AI tools.
"""DeepEval-based scoring for evaluation results.

Uses LLM-as-judge via DeepEval metrics to score RAG responses on
faithfulness (groundedness), answer relevancy, contextual precision,
and contextual relevancy. The judge model is configurable — defaults
to MaaS endpoint.
"""

import logging

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from openai import AsyncOpenAI, OpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)

HALLUCINATION_THRESHOLD = 0.7


class MaaSJudgeModel(DeepEvalBaseLLM):
    """OpenAI-compatible judge model for DeepEval, backed by MaaS endpoint."""

    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str,
    ):
        self._model_name = model_name
        self._base_url = (base_url or "").rstrip("/")
        t = (api_key or "").strip()
        if t.lower().startswith("bearer "):
            t = t[7:].strip()
        self._api_key = t
        self._sync_client = OpenAI(base_url=self._base_url + "/v1", api_key=self._api_key)
        self._async_client = AsyncOpenAI(base_url=self._base_url + "/v1", api_key=self._api_key)
        super().__init__(model=model_name)

    def load_model(self):
        return self._sync_client

    def generate(self, prompt: str) -> str:
        response = self._sync_client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str) -> str:
        response = await self._async_client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content

    def get_model_name(self) -> str:
        return self._model_name


def _get_judge_model() -> DeepEvalBaseLLM:
    """Create judge model from settings."""
    return MaaSJudgeModel(
        model_name=settings.resolved_judge_model_name,
        base_url=settings.MAAS_ENDPOINT,
        api_key=settings.api_token_bare,
    )


async def score_result(
    question: str,
    answer: str,
    contexts: list[str],
    expected_answer: str | None = None,
) -> dict:
    """Score a single RAG response using DeepEval metrics.

    Args:
        question: The input question.
        answer: The model's generated answer.
        contexts: Retrieved context chunks used for generation.
        expected_answer: Optional ground truth answer. Required for
            context precision scoring.

    Returns:
        Dict with relevancy_score, groundedness_score,
        context_precision_score, context_relevancy_score,
        and is_hallucination.
    """
    if not settings.API_TOKEN:
        logger.warning("No API token for judge model, skipping scoring")
        return {}

    if not settings.resolved_judge_model_name:
        logger.warning(
            "No judge model name configured (set JUDGE_MODEL_NAME or MODEL_A_NAME), skipping scoring"
        )
        return {}

    judge = _get_judge_model()

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        retrieval_context=contexts,
        expected_output=expected_answer,
    )

    scores: dict = {}

    metrics: list[tuple[str, object]] = [
        ("groundedness_score", FaithfulnessMetric(model=judge, threshold=0.5, async_mode=True)),
        ("relevancy_score", AnswerRelevancyMetric(model=judge, threshold=0.5, async_mode=True)),
        (
            "context_relevancy_score",
            ContextualRelevancyMetric(model=judge, threshold=0.5, async_mode=True),
        ),
    ]

    # ContextualPrecisionMetric requires expected_output (ground truth)
    if expected_answer:
        metrics.append((
            "context_precision_score",
            ContextualPrecisionMetric(model=judge, threshold=0.5, async_mode=True),
        ))

    for name, metric in metrics:
        try:
            await metric.a_measure(test_case)
            scores[name] = metric.score
        except Exception as e:
            logger.error("Scoring failed for %s: %s", name, e, exc_info=True)
            scores[name] = None

    groundedness = scores.get("groundedness_score")
    if groundedness is not None:
        scores["is_hallucination"] = groundedness < HALLUCINATION_THRESHOLD
    else:
        scores["is_hallucination"] = None

    return scores
