# This project was developed with assistance from AI tools.
"""Pydantic schemas for the evaluation endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EvalRunCreate(BaseModel):
    """Request to create a new evaluation run."""

    model_name: str = Field(..., min_length=1)
    questions: list[str] = Field(..., min_length=1, max_length=100)


class EvalResultResponse(BaseModel):
    """Response for a single evaluation result."""

    id: int
    question: str
    answer: str | None = None
    contexts: str | None = None
    latency_ms: float | None = None
    relevancy_score: float | None = None
    groundedness_score: float | None = None
    context_precision_score: float | None = None
    context_relevancy_score: float | None = None
    is_hallucination: bool | None = None
    total_tokens: int | None = None
    error_message: str | None = None


class EvalRunResponse(BaseModel):
    """Response for an evaluation run."""

    id: int
    model_name: str
    status: Literal["pending", "running", "completed", "failed"]
    total_questions: int
    completed_questions: int
    avg_latency_ms: float | None = None
    avg_relevancy: float | None = None
    avg_groundedness: float | None = None
    avg_context_precision: float | None = None
    avg_context_relevancy: float | None = None
    hallucination_rate: float | None = None
    total_tokens: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class EvalRunDetailResponse(EvalRunResponse):
    """Evaluation run with individual results."""

    results: list[EvalResultResponse] = []


class EvalRunCreateResponse(BaseModel):
    """Response after creating an evaluation run."""

    eval_run_id: int
    model_name: str
    status: str
    total_questions: int
    message: str


class EvalRunRerun(BaseModel):
    """Request to re-run an evaluation with a different model."""

    model_name: str = Field(..., min_length=1)


class ComparisonMetric(BaseModel):
    """A single metric compared across two runs."""

    metric: str
    run_a: float | None = None
    run_b: float | None = None
    winner: str | None = None


class QuestionComparison(BaseModel):
    """Side-by-side comparison of a single question across two runs."""

    question: str
    run_a: EvalResultResponse | None = None
    run_b: EvalResultResponse | None = None


class ComparisonResponse(BaseModel):
    """Side-by-side comparison of two evaluation runs."""

    run_a: EvalRunResponse
    run_b: EvalRunResponse
    metrics: list[ComparisonMetric] = []
    questions: list[QuestionComparison] = []


class SynthesizeRequest(BaseModel):
    """Request to auto-generate evaluation questions from documents."""

    document_ids: list[int] | None = Field(
        default=None, description="Document IDs to generate from. None = all documents."
    )
    max_questions: int = Field(default=10, ge=1, le=50)


class SynthesizedQuestion(BaseModel):
    """A single auto-generated question with expected answer."""

    question: str
    expected_answer: str | None = None


class SynthesizeResponse(BaseModel):
    """Response with auto-generated evaluation questions."""

    questions: list[SynthesizedQuestion] = []
    count: int = 0
