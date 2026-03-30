# This project was developed with assistance from AI tools.
"""Pydantic schemas for question set endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionSetCreate(BaseModel):
    """Request to create a question set."""

    name: str = Field(..., min_length=1, max_length=200)
    questions: list[str] = Field(..., min_length=1, max_length=100)


class QuestionSetResponse(BaseModel):
    """Response for a question set."""

    id: int
    name: str
    questions: list[str]
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
