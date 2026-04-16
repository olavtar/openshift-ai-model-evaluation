# This project was developed with assistance from AI tools.
"""Question set endpoints -- create, list, and delete reusable question sets."""

import logging

from db import QuestionSet, get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.question_set import QuestionSetCreate, QuestionSetItem, QuestionSetResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_response(qs: QuestionSet) -> QuestionSetResponse:
    """Build response, normalizing old plain-string questions to objects."""
    items = []
    for q in qs.questions:
        if isinstance(q, str):
            items.append(QuestionSetItem(question=q))
        elif isinstance(q, dict):
            items.append(QuestionSetItem(**q))
        else:
            items.append(q)
    return QuestionSetResponse(
        id=qs.id,
        name=qs.name,
        questions=items,
        created_at=qs.created_at,
    )


@router.post("/", response_model=QuestionSetResponse, status_code=201)
async def create_question_set(
    request: QuestionSetCreate,
    session: AsyncSession = Depends(get_db),
) -> QuestionSetResponse:
    """Save a reusable set of evaluation questions."""
    normalized = []
    for q in request.questions:
        if isinstance(q, str):
            normalized.append({"question": q})
        else:
            normalized.append(q.model_dump(exclude_none=True))
    qs = QuestionSet(name=request.name, questions=normalized)
    session.add(qs)
    await session.flush()
    response = _build_response(qs)
    await session.commit()
    return response


@router.get("/", response_model=list[QuestionSetResponse])
async def list_question_sets(
    session: AsyncSession = Depends(get_db),
) -> list[QuestionSetResponse]:
    """List all saved question sets, most recent first."""
    result = await session.execute(select(QuestionSet).order_by(QuestionSet.created_at.desc()))
    return [_build_response(qs) for qs in result.scalars().all()]


@router.get("/{question_set_id}", response_model=QuestionSetResponse)
async def get_question_set(
    question_set_id: int,
    session: AsyncSession = Depends(get_db),
) -> QuestionSetResponse:
    """Get a single question set by ID."""
    qs = await session.get(QuestionSet, question_set_id)
    if not qs:
        raise HTTPException(status_code=404, detail="Question set not found")
    return _build_response(qs)


@router.delete("/{question_set_id}", status_code=204)
async def delete_question_set(
    question_set_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a question set."""
    qs = await session.get(QuestionSet, question_set_id)
    if not qs:
        raise HTTPException(status_code=404, detail="Question set not found")
    await session.delete(qs)
    await session.commit()
