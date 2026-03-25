# This project was developed with assistance from AI tools.
"""Pydantic schemas for the evaluation endpoints."""

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
    is_hallucination: bool | None = None
    total_tokens: int | None = None
    error_message: str | None = None


class EvalRunResponse(BaseModel):
    """Response for an evaluation run."""

    id: int
    model_name: str
    status: str
    total_questions: int
    completed_questions: int
    avg_latency_ms: float | None = None
    avg_relevancy: float | None = None
    avg_groundedness: float | None = None
    avg_context_precision: float | None = None
    hallucination_rate: float | None = None
    total_tokens: int | None = None
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

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
