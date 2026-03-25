# This project was developed with assistance from AI tools.
"""DeepEval-based scoring for evaluation results.

Uses LLM-as-judge via DeepEval metrics to score RAG responses on
faithfulness (groundedness), answer relevancy, and contextual precision.
The judge model is configurable — defaults to MaaS endpoint.
"""

import logging

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
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
        self._base_url = base_url
        self._api_key = api_key
        super().__init__(model=model_name)

    def load_model(self):
        return OpenAI(base_url=self._base_url + "/v1", api_key=self._api_key)

    def generate(self, prompt: str, schema=None) -> str:
        response = self.model.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str, schema=None) -> str:
        client = AsyncOpenAI(base_url=self._base_url + "/v1", api_key=self._api_key)
        response = await client.chat.completions.create(
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
        model_name=settings.JUDGE_MODEL_NAME,
        base_url=settings.MAAS_ENDPOINT,
        api_key=settings.MODEL_API_TOKEN,
    )


async def score_result(
    question: str,
    answer: str,
    contexts: list[str],
) -> dict:
    """Score a single RAG response using DeepEval metrics.

    Args:
        question: The input question.
        answer: The model's generated answer.
        contexts: Retrieved context chunks used for generation.

    Returns:
        Dict with relevancy_score, groundedness_score,
        context_precision_score, and is_hallucination.
    """
    if not settings.MODEL_API_TOKEN:
        logger.warning("No MODEL_API_TOKEN set, skipping scoring")
        return {}

    judge = _get_judge_model()

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        retrieval_context=contexts,
    )

    scores: dict = {}

    metrics = [
        ("groundedness_score", FaithfulnessMetric(model=judge, threshold=0.5, async_mode=False)),
        ("relevancy_score", AnswerRelevancyMetric(model=judge, threshold=0.5, async_mode=False)),
        (
            "context_precision_score",
            ContextualPrecisionMetric(model=judge, threshold=0.5, async_mode=False),
        ),
    ]

    for name, metric in metrics:
        try:
            metric.measure(test_case)
            scores[name] = metric.score
        except Exception as e:
            logger.error("Scoring failed for %s: %s", name, e)
            scores[name] = None

    groundedness = scores.get("groundedness_score")
    if groundedness is not None:
        scores["is_hallucination"] = groundedness < HALLUCINATION_THRESHOLD
    else:
        scores["is_hallucination"] = None

    return scores
