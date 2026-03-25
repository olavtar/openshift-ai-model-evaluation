# This project was developed with assistance from AI tools.
"""Tests for DeepEval scoring service."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def _no_api_token():
    """Ensure no API token is set."""
    with patch("src.services.scoring.settings") as mock_settings:
        mock_settings.MODEL_API_TOKEN = ""
        yield mock_settings


@pytest.fixture
def _mock_settings():
    """Provide valid settings for scoring."""
    with patch("src.services.scoring.settings") as mock_settings:
        mock_settings.MODEL_API_TOKEN = "test-token"
        mock_settings.MAAS_ENDPOINT = "https://maas.example.com"
        mock_settings.JUDGE_MODEL_NAME = "granite-3.1-8b-instruct"
        yield mock_settings


@pytest.mark.asyncio
async def test_score_result_skips_when_no_token(_no_api_token):
    """Should return empty dict when no API token is configured."""
    from src.services.scoring import score_result

    result = await score_result(
        question="What is AI?",
        answer="AI is artificial intelligence.",
        contexts=["AI stands for artificial intelligence."],
    )
    assert result == {}


@pytest.mark.asyncio
async def test_score_result_returns_all_metrics(_mock_settings):
    """Should return all metric scores when scoring succeeds."""
    from src.services.scoring import score_result

    mock_metric = MagicMock()
    mock_metric.score = 0.85
    mock_metric.measure = MagicMock()

    with patch("src.services.scoring.FaithfulnessMetric", return_value=mock_metric), \
         patch("src.services.scoring.AnswerRelevancyMetric", return_value=mock_metric), \
         patch("src.services.scoring.ContextualPrecisionMetric", return_value=mock_metric):
        result = await score_result(
            question="What is AI?",
            answer="AI is artificial intelligence.",
            contexts=["AI stands for artificial intelligence."],
        )

    assert result["groundedness_score"] == 0.85
    assert result["relevancy_score"] == 0.85
    assert result["context_precision_score"] == 0.85
    assert result["is_hallucination"] is False


@pytest.mark.asyncio
async def test_score_result_detects_hallucination(_mock_settings):
    """Should flag hallucination when groundedness score is below threshold."""
    from src.services.scoring import score_result

    low_score_metric = MagicMock()
    low_score_metric.score = 0.4
    low_score_metric.measure = MagicMock()

    high_score_metric = MagicMock()
    high_score_metric.score = 0.9
    high_score_metric.measure = MagicMock()

    with patch("src.services.scoring.FaithfulnessMetric", return_value=low_score_metric), \
         patch("src.services.scoring.AnswerRelevancyMetric", return_value=high_score_metric), \
         patch("src.services.scoring.ContextualPrecisionMetric", return_value=high_score_metric):
        result = await score_result(
            question="What is the capital requirement?",
            answer="Banks need 50% capital reserves.",
            contexts=["Basel III requires 8% minimum capital."],
        )

    assert result["groundedness_score"] == 0.4
    assert result["is_hallucination"] is True


@pytest.mark.asyncio
async def test_score_result_handles_metric_failure(_mock_settings):
    """Should return None for a metric that fails and continue with others."""
    from src.services.scoring import score_result

    failing_metric = MagicMock()
    failing_metric.measure = MagicMock(side_effect=RuntimeError("Judge model unavailable"))

    ok_metric = MagicMock()
    ok_metric.score = 0.9
    ok_metric.measure = MagicMock()

    with patch("src.services.scoring.FaithfulnessMetric", return_value=failing_metric), \
         patch("src.services.scoring.AnswerRelevancyMetric", return_value=ok_metric), \
         patch("src.services.scoring.ContextualPrecisionMetric", return_value=ok_metric):
        result = await score_result(
            question="What is AI?",
            answer="AI is artificial intelligence.",
            contexts=["AI stands for artificial intelligence."],
        )

    assert result["groundedness_score"] is None
    assert result["relevancy_score"] == 0.9
    assert result["context_precision_score"] == 0.9
    assert result["is_hallucination"] is None


@pytest.mark.asyncio
async def test_maas_judge_model_get_model_name():
    """MaaSJudgeModel should return the configured model name."""
    from src.services.scoring import MaaSJudgeModel

    judge = MaaSJudgeModel(
        model_name="granite-3.1-8b-instruct",
        base_url="https://maas.example.com",
        api_key="test-token",
    )
    assert judge.get_model_name() == "granite-3.1-8b-instruct"
