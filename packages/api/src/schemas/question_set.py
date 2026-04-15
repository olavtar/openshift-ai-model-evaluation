# This project was developed with assistance from AI tools.
"""Pydantic schemas for question set endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionSetItem(BaseModel):
    """A single question with optional expected answer."""

    question: str = Field(..., min_length=1)
    expected_answer: str | None = None
    expected_chunks: list[str] | None = Field(
        default=None, description='Expected source chunks, e.g. ["report.pdf:3", "guide.pdf"].'
    )


class QuestionSetCreate(BaseModel):
    """Request to create a question set."""

    name: str = Field(..., min_length=1, max_length=200)
    questions: list[str | QuestionSetItem] = Field(..., min_length=1, max_length=100)


class QuestionSetResponse(BaseModel):
    """Response for a question set."""

    id: int
    name: str
    questions: list[QuestionSetItem]
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
