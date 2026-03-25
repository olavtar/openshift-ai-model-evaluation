# This project was developed with assistance from AI tools.
"""Evaluation endpoints -- create, list, and inspect evaluation runs."""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import EvalResult, EvalRun, get_db

from ..schemas.evaluation import (
    EvalResultResponse,
    EvalRunCreate,
    EvalRunCreateResponse,
    EvalRunDetailResponse,
    EvalRunResponse,
)
from ..services.generation import generate_answer
from ..services.retrieval import retrieve_chunks

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_evaluation(eval_run_id: int, model_name: str, questions: list[str]) -> None:
    """Execute an evaluation run in the background.

    For each question: retrieve context, generate answer, record results.
    Metric scoring (groundedness, relevancy, etc.) is deferred to PR 9.
    """
    from db.database import SessionLocal

    async with SessionLocal() as session:
        run = await session.get(EvalRun, eval_run_id)
        if not run:
            return

        run.status = "running"
        await session.commit()

        total_latency = 0.0
        total_tokens_sum = 0
        completed = 0

        for question in questions:
            start = time.time()
            try:
                chunks = await retrieve_chunks(query=question, session=session)
                result = await generate_answer(
                    question=question,
                    chunks=chunks,
                    model_name=model_name,
                )
                latency = (time.time() - start) * 1000
                tokens = result.get("usage", {}).get("total_tokens") if result.get("usage") else None

                contexts_str = "\n---\n".join(c["text"] for c in chunks) if chunks else None

                eval_result = EvalResult(
                    eval_run_id=eval_run_id,
                    question=question,
                    answer=result["answer"],
                    contexts=contexts_str,
                    latency_ms=latency,
                    total_tokens=tokens,
                )
                session.add(eval_result)

                total_latency += latency
                if tokens:
                    total_tokens_sum += tokens
                completed += 1

            except Exception as e:
                logger.error("Eval question failed: %s", e)
                eval_result = EvalResult(
                    eval_run_id=eval_run_id,
                    question=question,
                    error_message=str(e),
                )
                session.add(eval_result)
                completed += 1

            run.completed_questions = completed
            await session.commit()

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.avg_latency_ms = total_latency / len(questions) if questions else None
        run.total_tokens = total_tokens_sum or None
        await session.commit()


@router.post("/", response_model=EvalRunCreateResponse, status_code=201)
async def create_eval_run(
    request: EvalRunCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> EvalRunCreateResponse:
    """Create a new evaluation run.

    Queues the evaluation to run in the background. Each question is
    sent through the RAG pipeline using the specified model.
    """
    run = EvalRun(
        model_name=request.model_name,
        status="pending",
        total_questions=len(request.questions),
    )
    session.add(run)
    await session.flush()

    background_tasks.add_task(
        _run_evaluation,
        eval_run_id=run.id,
        model_name=request.model_name,
        questions=request.questions,
    )

    await session.commit()

    return EvalRunCreateResponse(
        eval_run_id=run.id,
        model_name=run.model_name,
        status=run.status,
        total_questions=run.total_questions,
        message=f"Evaluation started with {len(request.questions)} questions",
    )


@router.get("/", response_model=list[EvalRunResponse])
async def list_eval_runs(
    session: AsyncSession = Depends(get_db),
) -> list[EvalRunResponse]:
    """List all evaluation runs, most recent first."""
    result = await session.execute(
        select(EvalRun).order_by(EvalRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        EvalRunResponse(
            id=r.id,
            model_name=r.model_name,
            status=r.status,
            total_questions=r.total_questions,
            completed_questions=r.completed_questions,
            avg_latency_ms=r.avg_latency_ms,
            avg_relevancy=r.avg_relevancy,
            avg_groundedness=r.avg_groundedness,
            avg_context_precision=r.avg_context_precision,
            hallucination_rate=r.hallucination_rate,
            total_tokens=r.total_tokens,
            error_message=r.error_message,
            created_at=r.created_at.isoformat() if r.created_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
        for r in runs
    ]


@router.get("/{eval_run_id}", response_model=EvalRunDetailResponse)
async def get_eval_run(
    eval_run_id: int,
    session: AsyncSession = Depends(get_db),
) -> EvalRunDetailResponse:
    """Get an evaluation run with its individual results."""
    run = await session.get(EvalRun, eval_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    results = await session.execute(
        select(EvalResult)
        .where(EvalResult.eval_run_id == eval_run_id)
        .order_by(EvalResult.id)
    )
    result_rows = results.scalars().all()

    return EvalRunDetailResponse(
        id=run.id,
        model_name=run.model_name,
        status=run.status,
        total_questions=run.total_questions,
        completed_questions=run.completed_questions,
        avg_latency_ms=run.avg_latency_ms,
        avg_relevancy=run.avg_relevancy,
        avg_groundedness=run.avg_groundedness,
        avg_context_precision=run.avg_context_precision,
        hallucination_rate=run.hallucination_rate,
        total_tokens=run.total_tokens,
        error_message=run.error_message,
        created_at=run.created_at.isoformat() if run.created_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        results=[
            EvalResultResponse(
                id=r.id,
                question=r.question,
                answer=r.answer,
                contexts=r.contexts,
                latency_ms=r.latency_ms,
                relevancy_score=r.relevancy_score,
                groundedness_score=r.groundedness_score,
                context_precision_score=r.context_precision_score,
                is_hallucination=r.is_hallucination,
                total_tokens=r.total_tokens,
                error_message=r.error_message,
            )
            for r in result_rows
        ],
    )
