# This project was developed with assistance from AI tools.
"""Tests for DeepEval scoring service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def _no_api_token():
    """Ensure no API token is set."""
    with patch("src.services.scoring.settings") as mock_settings:
        mock_settings.API_TOKEN = ""
        yield mock_settings


@pytest.fixture
def _mock_settings():
    """Provide valid settings for scoring."""
    with patch("src.services.scoring.settings") as mock_settings:
        mock_settings.API_TOKEN = "test-token"
        mock_settings.MAAS_ENDPOINT = "https://maas.example.com"
        mock_settings.JUDGE_MODEL_NAME = "granite-3.1-8b-instruct"
        mock_settings.MODEL_A_NAME = ""
        mock_settings.MODEL_B_NAME = ""
        mock_settings.resolved_judge_model_name = "granite-3.1-8b-instruct"
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
async def test_score_result_skips_when_no_judge_model_name():
    """Should return empty dict when token is set but no judge/chat model name."""
    from src.services.scoring import score_result

    with patch("src.services.scoring.settings") as mock_settings:
        mock_settings.API_TOKEN = "test-token"
        mock_settings.resolved_judge_model_name = ""

        result = await score_result(
            question="What is AI?",
            answer="AI is artificial intelligence.",
            contexts=["AI stands for artificial intelligence."],
            evaluated_model_name="",
        )

    assert result == {}


@pytest.mark.asyncio
async def test_score_result_uses_evaluated_model_when_no_env_judge():
    """Should use evaluated_model_name as judge when env judge chain is empty."""
    from src.services.scoring import score_result

    mock_metric = MagicMock()
    mock_metric.score = 0.8
    mock_metric.a_measure = AsyncMock()

    with patch("src.services.scoring.settings") as mock_settings:
        mock_settings.API_TOKEN = "test-token"
        mock_settings.MAAS_ENDPOINT = "https://maas.example.com"
        mock_settings.JUDGE_MODEL_NAME = ""
        mock_settings.MODEL_A_NAME = ""
        mock_settings.MODEL_B_NAME = ""
        mock_settings.resolved_judge_model_name = ""
        mock_settings.api_token_bare = "test-token"

        with (
            patch("src.services.scoring.FaithfulnessMetric", return_value=mock_metric),
            patch("src.services.scoring.AnswerRelevancyMetric", return_value=mock_metric),
            patch("src.services.scoring.ContextualRelevancyMetric", return_value=mock_metric),
            patch("src.services.scoring._abstention_metric", return_value=mock_metric),
            patch("src.services.scoring.MaaSJudgeModel") as mock_judge_cls,
        ):
            result = await score_result(
                question="What is AI?",
                answer="AI is artificial intelligence.",
                contexts=["AI stands for artificial intelligence."],
                evaluated_model_name="qwen3-14b",
            )

    mock_judge_cls.assert_called_once()
    assert mock_judge_cls.call_args.kwargs["model_name"] == "qwen3-14b"
    assert result.get("relevancy_score") == 0.8


@pytest.mark.asyncio
async def test_score_result_returns_all_metrics(_mock_settings):
    """Should return all metric scores when scoring succeeds with expected_answer."""
    from src.services.scoring import score_result

    mock_metric = MagicMock()
    mock_metric.score = 0.85
    mock_metric.a_measure = AsyncMock()

    with (
        patch("src.services.scoring.FaithfulnessMetric", return_value=mock_metric),
        patch("src.services.scoring.AnswerRelevancyMetric", return_value=mock_metric),
        patch("src.services.scoring.ContextualPrecisionMetric", return_value=mock_metric),
        patch("src.services.scoring.ContextualRelevancyMetric", return_value=mock_metric),
        patch("src.services.scoring._abstention_metric", return_value=mock_metric),
        patch("src.services.scoring._completeness_metric", return_value=mock_metric),
        patch("src.services.scoring._correctness_metric", return_value=mock_metric),
        patch("src.services.scoring._compliance_accuracy_metric", return_value=mock_metric),
    ):
        result = await score_result(
            question="What is AI?",
            answer="AI is artificial intelligence.",
            contexts=["AI stands for artificial intelligence."],
            expected_answer="AI is artificial intelligence.",
        )

    assert result["groundedness_score"] == 0.85
    assert result["relevancy_score"] == 0.85
    assert result["context_precision_score"] == 0.85
    assert result["context_relevancy_score"] == 0.85
    assert result["abstention_score"] == 0.85
    assert result["completeness_score"] == 0.85
    assert result["correctness_score"] == 0.85
    assert result["compliance_accuracy_score"] == 0.85
    assert result["is_hallucination"] is False


@pytest.mark.asyncio
async def test_score_result_detects_hallucination(_mock_settings):
    """Should flag hallucination when groundedness score is below threshold."""
    from src.services.scoring import score_result

    low_score_metric = MagicMock()
    low_score_metric.score = 0.4
    low_score_metric.a_measure = AsyncMock()

    high_score_metric = MagicMock()
    high_score_metric.score = 0.9
    high_score_metric.a_measure = AsyncMock()

    with (
        patch("src.services.scoring.FaithfulnessMetric", return_value=low_score_metric),
        patch("src.services.scoring.AnswerRelevancyMetric", return_value=high_score_metric),
        patch("src.services.scoring.ContextualRelevancyMetric", return_value=high_score_metric),
        patch("src.services.scoring._abstention_metric", return_value=high_score_metric),
    ):
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
    failing_metric.a_measure = AsyncMock(side_effect=RuntimeError("Judge model unavailable"))

    ok_metric = MagicMock()
    ok_metric.score = 0.9
    ok_metric.a_measure = AsyncMock()

    with (
        patch("src.services.scoring.FaithfulnessMetric", return_value=failing_metric),
        patch("src.services.scoring.AnswerRelevancyMetric", return_value=ok_metric),
        patch("src.services.scoring.ContextualPrecisionMetric", return_value=ok_metric),
        patch("src.services.scoring.ContextualRelevancyMetric", return_value=ok_metric),
        patch("src.services.scoring._abstention_metric", return_value=ok_metric),
        patch("src.services.scoring._completeness_metric", return_value=ok_metric),
        patch("src.services.scoring._correctness_metric", return_value=ok_metric),
        patch("src.services.scoring._compliance_accuracy_metric", return_value=ok_metric),
    ):
        result = await score_result(
            question="What is AI?",
            answer="AI is artificial intelligence.",
            contexts=["AI stands for artificial intelligence."],
            expected_answer="AI is artificial intelligence.",
        )

    assert result["groundedness_score"] is None
    assert result["relevancy_score"] == 0.9
    assert result["context_precision_score"] == 0.9
    assert result["context_relevancy_score"] == 0.9
    assert result["abstention_score"] == 0.9
    assert result["completeness_score"] == 0.9
    assert result["is_hallucination"] is None


@pytest.mark.asyncio
async def test_score_result_without_expected_answer(_mock_settings):
    """Should omit context_precision_score when no expected_answer is provided."""
    from src.services.scoring import score_result

    mock_metric = MagicMock()
    mock_metric.score = 0.85
    mock_metric.a_measure = AsyncMock()

    with (
        patch("src.services.scoring.FaithfulnessMetric", return_value=mock_metric),
        patch("src.services.scoring.AnswerRelevancyMetric", return_value=mock_metric),
        patch("src.services.scoring.ContextualRelevancyMetric", return_value=mock_metric),
        patch("src.services.scoring._abstention_metric", return_value=mock_metric),
    ):
        result = await score_result(
            question="What is AI?",
            answer="AI is artificial intelligence.",
            contexts=["AI stands for artificial intelligence."],
        )

    assert "groundedness_score" in result
    assert "relevancy_score" in result
    assert "context_relevancy_score" in result
    assert "abstention_score" in result
    assert "context_precision_score" not in result
    assert "completeness_score" not in result
    assert "correctness_score" not in result
    assert "compliance_accuracy_score" not in result
    assert result["is_hallucination"] is False


def test_maas_judge_model_get_model_name():
    """MaaSJudgeModel should return the configured model name."""
    from src.services.scoring import MaaSJudgeModel

    judge = MaaSJudgeModel(
        model_name="granite-3.1-8b-instruct",
        base_url="https://maas.example.com",
        api_key="test-token",
    )
    assert judge.get_model_name() == "granite-3.1-8b-instruct"


# --- Chunk alignment tests ---


def test_chunk_alignment_perfect_match():
    """Should return 1.0 when all expected chunks are retrieved."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"source_document": "report.pdf", "page_number": "3"},
        {"source_document": "guide.pdf", "page_number": "1"},
    ]
    expected = ["report.pdf:3", "guide.pdf:1"]
    assert compute_chunk_alignment(retrieved, expected) == 1.0


def test_chunk_alignment_partial_match():
    """Should return fraction of matched expected chunks."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"source_document": "report.pdf", "page_number": "3"},
        {"source_document": "other.pdf", "page_number": "5"},
    ]
    expected = ["report.pdf:3", "guide.pdf:1"]
    assert compute_chunk_alignment(retrieved, expected) == 0.5


def test_chunk_alignment_no_match():
    """Should return 0.0 when no expected chunks are retrieved."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"source_document": "other.pdf", "page_number": "1"},
    ]
    expected = ["report.pdf:3", "guide.pdf:1"]
    assert compute_chunk_alignment(retrieved, expected) == 0.0


def test_chunk_alignment_doc_only_match():
    """Should match on document name when no page is specified in expected."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"source_document": "report.pdf", "page_number": "7"},
    ]
    expected = ["report.pdf"]
    assert compute_chunk_alignment(retrieved, expected) == 1.0


def test_chunk_alignment_empty_expected():
    """Should return 1.0 when no expected chunks are specified."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [{"source_document": "report.pdf", "page_number": "1"}]
    assert compute_chunk_alignment(retrieved, []) == 1.0


def test_chunk_alignment_empty_retrieved():
    """Should return 0.0 when nothing was retrieved but chunks were expected."""
    from src.services.scoring import compute_chunk_alignment

    assert compute_chunk_alignment([], ["report.pdf:3"]) == 0.0


def test_chunk_alignment_mixed_format():
    """Should handle mix of doc-only and doc:page expected chunks."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"source_document": "report.pdf", "page_number": "3"},
        {"source_document": "guide.pdf", "page_number": None},
    ]
    expected = ["report.pdf:3", "guide.pdf"]
    assert compute_chunk_alignment(retrieved, expected) == 1.0


def test_chunk_alignment_chunk_id_format():
    """Should match chunk:{id} refs against retrieved chunk IDs."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"id": 42, "source_document": "guide.pdf", "page_number": "3"},
        {"id": 43, "source_document": "guide.pdf", "page_number": "4"},
        {"id": 67, "source_document": "report.pdf", "page_number": "1"},
    ]
    expected = ["chunk:42", "chunk:67"]
    assert compute_chunk_alignment(retrieved, expected) == 1.0


def test_chunk_alignment_chunk_id_partial():
    """Should return fraction when some chunk:{id} refs are not retrieved."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"id": 42, "source_document": "guide.pdf", "page_number": "3"},
    ]
    expected = ["chunk:42", "chunk:99"]
    assert compute_chunk_alignment(retrieved, expected) == 0.5


def test_chunk_alignment_mixed_chunk_id_and_legacy():
    """Should handle mix of chunk:{id} and legacy filename refs."""
    from src.services.scoring import compute_chunk_alignment

    retrieved = [
        {"id": 42, "source_document": "guide.pdf", "page_number": "3"},
        {"id": 43, "source_document": "report.pdf", "page_number": "1"},
    ]
    expected = ["chunk:42", "report.pdf:1"]
    assert compute_chunk_alignment(retrieved, expected) == 1.0


def test_resolved_judge_model_name_order():
    """Judge model should prefer JUDGE_MODEL_NAME, then MODEL_A_NAME, then MODEL_B_NAME."""
    from src.core.config import Settings

    s = Settings(
        JUDGE_MODEL_NAME="judge-m",
        MODEL_A_NAME="model-a",
        MODEL_B_NAME="model-b",
        MAAS_ENDPOINT="https://x",
        API_TOKEN="t",
    )
    assert s.resolved_judge_model_name == "judge-m"

    s2 = Settings(
        JUDGE_MODEL_NAME="",
        MODEL_A_NAME="model-a",
        MODEL_B_NAME="model-b",
        MAAS_ENDPOINT="https://x",
        API_TOKEN="t",
    )
    assert s2.resolved_judge_model_name == "model-a"

    s3 = Settings(
        JUDGE_MODEL_NAME="",
        MODEL_A_NAME="",
        MODEL_B_NAME="model-b",
        MAAS_ENDPOINT="https://x",
        API_TOKEN="t",
    )
    assert s3.resolved_judge_model_name == "model-b"
