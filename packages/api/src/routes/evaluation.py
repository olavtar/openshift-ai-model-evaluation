# This project was developed with assistance from AI tools.
"""Evaluation endpoints -- create, list, and inspect evaluation runs."""

import logging
import time
from datetime import UTC, datetime

from db import EvalResult, EvalRun, get_db
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..schemas.evaluation import (
    ComparisonMetric,
    ComparisonResponse,
    EvalQuestion,
    EvalResultResponse,
    EvalRunCreate,
    EvalRunCreateResponse,
    EvalRunDetailResponse,
    EvalRunRerun,
    EvalRunResponse,
    QuestionComparison,
    SynthesizedQuestion,
    SynthesizeRequest,
    SynthesizeResponse,
)
from ..services.generation import generate_answer
from ..services.profiles import load_profile
from ..services.retrieval import retrieve_chunks
from ..services.scoring import score_result
from ..services.synthesizer import generate_questions
from ..services.verdicts import QuestionVerdict, compute_question_verdict, compute_run_verdict

logger = logging.getLogger(__name__)
router = APIRouter()

COMPARISON_TIE_THRESHOLD = 0.05

# In-memory set of run IDs that have been requested to cancel.
# The background task checks this between questions and stops early.
_cancelled_runs: set[int] = set()


async def _run_evaluation(
    eval_run_id: int,
    model_name: str,
    questions: list[EvalQuestion],
    profile_id: str | None = None,
) -> None:
    """Execute an evaluation run in the background.

    For each question: retrieve context, generate answer, score with DeepEval
    metrics (faithfulness, relevancy, context precision, context relevancy,
    completeness, correctness, compliance accuracy, abstention), record results.
    """
    from db.database import SessionLocal

    async with SessionLocal() as session:
        run = await session.get(EvalRun, eval_run_id)
        if not run:
            return

        run.status = "running"
        if profile_id:
            run.profile_id = profile_id
        await session.commit()

        # Load profile for verdict computation (if specified)
        profile = None
        if profile_id:
            try:
                profile = load_profile(profile_id)
                run.profile_version = profile.version
            except (FileNotFoundError, ValueError) as e:
                logger.warning("Could not load profile '%s': %s", profile_id, e)

        try:
            total_latency = 0.0
            total_tokens_sum = 0
            completed = 0
            all_relevancy = []
            all_groundedness = []
            all_context_precision = []
            all_context_relevancy = []
            all_completeness = []
            all_correctness = []
            all_compliance_accuracy = []
            all_abstention = []
            hallucination_count = 0
            hallucination_scored_count = 0
            question_verdicts: list[QuestionVerdict] = []

            def _is_cancelled() -> bool:
                return eval_run_id in _cancelled_runs

            for q_item in questions:
                if _is_cancelled():
                    break

                question = q_item.question
                expected_answer = q_item.expected_answer

                start = time.time()
                try:
                    chunks = await retrieve_chunks(query=question, session=session)

                    if _is_cancelled():
                        break

                    result = await generate_answer(
                        question=question,
                        chunks=chunks,
                        model_name=model_name,
                    )
                    latency = (time.time() - start) * 1000
                    tokens = (
                        result.get("usage", {}).get("total_tokens")
                        if result.get("usage")
                        else None
                    )

                    context_texts = [c["text"] for c in chunks] if chunks else []
                    # Format context with source metadata for UI display
                    if chunks:
                        context_parts = []
                        for c in chunks:
                            header_parts = [c.get("source_document", "")]
                            if c.get("page_number"):
                                header_parts.append(f"p.{c['page_number']}")
                            if c.get("section_path"):
                                header_parts.append(c["section_path"])
                            header = " | ".join(p for p in header_parts if p)
                            context_parts.append(f"[{header}]\n{c['text']}")
                        contexts_str = "\n---\n".join(context_parts)
                    else:
                        contexts_str = None

                    if _is_cancelled():
                        break

                    scores = {}
                    if result["answer"] and context_texts:
                        scores = await score_result(
                            question=question,
                            answer=result["answer"],
                            contexts=context_texts,
                            expected_answer=expected_answer,
                        )

                    eval_result = EvalResult(
                        eval_run_id=eval_run_id,
                        question=question,
                        answer=result["answer"],
                        contexts=contexts_str,
                        latency_ms=latency,
                        relevancy_score=scores.get("relevancy_score"),
                        groundedness_score=scores.get("groundedness_score"),
                        context_precision_score=scores.get("context_precision_score"),
                        context_relevancy_score=scores.get("context_relevancy_score"),
                        completeness_score=scores.get("completeness_score"),
                        correctness_score=scores.get("correctness_score"),
                        compliance_accuracy_score=scores.get("compliance_accuracy_score"),
                        abstention_score=scores.get("abstention_score"),
                        is_hallucination=scores.get("is_hallucination"),
                        total_tokens=tokens,
                    )

                    # Compute per-question verdict if profile is loaded
                    if profile and scores:
                        q_verdict = compute_question_verdict(scores, profile)
                        eval_result.verdict = q_verdict.verdict
                        eval_result.fail_reasons = q_verdict.fail_reasons
                        question_verdicts.append(q_verdict)

                    session.add(eval_result)

                    total_latency += latency
                    if tokens:
                        total_tokens_sum += tokens
                    if scores.get("relevancy_score") is not None:
                        all_relevancy.append(scores["relevancy_score"])
                    if scores.get("groundedness_score") is not None:
                        all_groundedness.append(scores["groundedness_score"])
                    if scores.get("context_precision_score") is not None:
                        all_context_precision.append(scores["context_precision_score"])
                    if scores.get("context_relevancy_score") is not None:
                        all_context_relevancy.append(scores["context_relevancy_score"])
                    if scores.get("completeness_score") is not None:
                        all_completeness.append(scores["completeness_score"])
                    if scores.get("correctness_score") is not None:
                        all_correctness.append(scores["correctness_score"])
                    if scores.get("compliance_accuracy_score") is not None:
                        all_compliance_accuracy.append(scores["compliance_accuracy_score"])
                    if scores.get("abstention_score") is not None:
                        all_abstention.append(scores["abstention_score"])
                    if scores.get("is_hallucination") is not None:
                        hallucination_scored_count += 1
                        if scores["is_hallucination"]:
                            hallucination_count += 1
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

            # Set final status
            if _is_cancelled():
                _cancelled_runs.discard(eval_run_id)
                run.status = "cancelled"
                run.completed_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                run.status = "completed"
                run.completed_at = datetime.now(UTC).replace(tzinfo=None)

            # Compute aggregates from whatever questions were completed
            run.avg_latency_ms = total_latency / completed if completed else None
            run.total_tokens = total_tokens_sum or None
            run.avg_relevancy = (
                sum(all_relevancy) / len(all_relevancy) if all_relevancy else None
            )
            run.avg_groundedness = (
                sum(all_groundedness) / len(all_groundedness) if all_groundedness else None
            )
            run.avg_context_precision = (
                sum(all_context_precision) / len(all_context_precision)
                if all_context_precision
                else None
            )
            run.avg_context_relevancy = (
                sum(all_context_relevancy) / len(all_context_relevancy)
                if all_context_relevancy
                else None
            )
            run.avg_completeness = (
                sum(all_completeness) / len(all_completeness) if all_completeness else None
            )
            run.avg_correctness = (
                sum(all_correctness) / len(all_correctness) if all_correctness else None
            )
            run.avg_compliance_accuracy = (
                sum(all_compliance_accuracy) / len(all_compliance_accuracy)
                if all_compliance_accuracy
                else None
            )
            run.avg_abstention = (
                sum(all_abstention) / len(all_abstention) if all_abstention else None
            )
            run.hallucination_rate = (
                hallucination_count / hallucination_scored_count
                if hallucination_scored_count > 0
                else None
            )

            # Compute run-level verdict
            if profile and question_verdicts:
                run_verdict = compute_run_verdict(question_verdicts)
                run.overall_verdict = run_verdict.overall
                run.pass_count = run_verdict.pass_count
                run.fail_count = run_verdict.fail_count
                run.review_count = run_verdict.review_count

            await session.commit()

        except Exception as e:
            logger.exception("Evaluation run failed: %s", e)
            if run.status != "cancelled":
                run.status = "failed"
                run.error_message = str(e)
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
    # Normalize questions: accept both plain strings and {question, expected_answer} objects
    normalized: list[EvalQuestion] = []
    for q in request.questions:
        if isinstance(q, str):
            normalized.append(EvalQuestion(question=q))
        else:
            normalized.append(q)

    run = EvalRun(
        model_name=request.model_name,
        question_set_id=request.question_set_id,
        status="pending",
        total_questions=len(normalized),
    )
    session.add(run)
    await session.flush()

    # Capture values before commit (commit expires ORM attributes in async context)
    run_id = run.id
    run_model = run.model_name
    run_status = run.status
    run_total = run.total_questions

    background_tasks.add_task(
        _run_evaluation,
        eval_run_id=run_id,
        model_name=request.model_name,
        questions=normalized,
        profile_id=request.profile_id,
    )

    await session.commit()

    message = f"Evaluation started with {len(request.questions)} questions"
    model_cfg = settings.get_model_config(request.model_name)
    if not model_cfg["token"]:
        message += f". Warning: No API token configured for {request.model_name}."
    elif not settings.resolved_judge_model_name:
        message += (
            ". Warning: No judge model name (JUDGE_MODEL_NAME or MODEL_A_NAME); "
            "faithfulness and related metrics will be skipped."
        )

    return EvalRunCreateResponse(
        eval_run_id=run_id,
        model_name=run_model,
        status=run_status,
        total_questions=run_total,
        message=message,
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
    return [_build_run_response(r) for r in runs]


@router.delete("/{eval_run_id}", status_code=204)
async def delete_eval_run(
    eval_run_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete an evaluation run and its results."""
    run = await session.get(EvalRun, eval_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    await session.delete(run)
    await session.commit()


@router.post("/{eval_run_id}/cancel")
async def cancel_eval_run(
    eval_run_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running or pending evaluation.

    Signals the background task to stop after the current question.
    Partial results are retained with aggregated scores.
    """
    run = await session.get(EvalRun, eval_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    if run.status not in ("pending", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel evaluation with status '{run.status}'",
        )

    _cancelled_runs.add(eval_run_id)

    # If still pending (background task hasn't started yet), mark directly
    if run.status == "pending":
        run.status = "cancelled"
        run.completed_at = datetime.now(UTC).replace(tzinfo=None)
        await session.commit()
        _cancelled_runs.discard(eval_run_id)

    return {"message": f"Cancellation requested for evaluation run #{eval_run_id}"}


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_questions(
    request: SynthesizeRequest,
    session: AsyncSession = Depends(get_db),
) -> SynthesizeResponse:
    """Auto-generate evaluation questions from ingested documents.

    Calls the shared MaaS chat endpoint (same path as RAG) with
    ``question_synthesis_model_name``. Optionally filter by document IDs.
    """
    if not settings.API_TOKEN:
        raise HTTPException(
            status_code=400,
            detail="No API token configured. Set API_TOKEN to enable question generation.",
        )
    if not settings.question_synthesis_model_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "No model configured for question synthesis. Set MODEL_A_NAME, "
                "JUDGE_MODEL_NAME, or QUESTION_SYNTHESIS_MODEL_NAME."
            ),
        )

    try:
        questions = await generate_questions(
            session=session,
            document_ids=request.document_ids,
            max_questions=request.max_questions,
        )
    except Exception as e:
        logger.exception("Question synthesis failed")
        raise HTTPException(
            status_code=500, detail=f"Question synthesis failed: {str(e)[:200]}"
        )
    return SynthesizeResponse(
        questions=[
            SynthesizedQuestion(
                question=q["question"],
                expected_answer=q.get("expected_answer"),
            )
            for q in questions
        ],
        count=len(questions),
    )


def _build_run_response(run: EvalRun) -> EvalRunResponse:
    """Build an EvalRunResponse from a model instance."""
    return EvalRunResponse(
        id=run.id,
        model_name=run.model_name,
        question_set_name=run.question_set.name if run.question_set else None,
        status=run.status,
        total_questions=run.total_questions,
        completed_questions=run.completed_questions,
        avg_latency_ms=run.avg_latency_ms,
        avg_relevancy=run.avg_relevancy,
        avg_groundedness=run.avg_groundedness,
        avg_context_precision=run.avg_context_precision,
        avg_context_relevancy=run.avg_context_relevancy,
        avg_completeness=run.avg_completeness,
        avg_correctness=run.avg_correctness,
        avg_compliance_accuracy=run.avg_compliance_accuracy,
        avg_abstention=run.avg_abstention,
        hallucination_rate=run.hallucination_rate,
        profile_id=run.profile_id,
        overall_verdict=run.overall_verdict,
        pass_count=run.pass_count,
        fail_count=run.fail_count,
        review_count=run.review_count,
        total_tokens=run.total_tokens,
        error_message=run.error_message,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


def _build_result_response(r: EvalResult) -> EvalResultResponse:
    """Build an EvalResultResponse from a model instance."""
    return EvalResultResponse(
        id=r.id,
        question=r.question,
        answer=r.answer,
        contexts=r.contexts,
        latency_ms=r.latency_ms,
        relevancy_score=r.relevancy_score,
        groundedness_score=r.groundedness_score,
        context_precision_score=r.context_precision_score,
        context_relevancy_score=r.context_relevancy_score,
        completeness_score=r.completeness_score,
        correctness_score=r.correctness_score,
        compliance_accuracy_score=r.compliance_accuracy_score,
        abstention_score=r.abstention_score,
        is_hallucination=r.is_hallucination,
        verdict=r.verdict,
        fail_reasons=r.fail_reasons,
        total_tokens=r.total_tokens,
        error_message=r.error_message,
    )


def _compare_metric(
    name: str, val_a: float | None, val_b: float | None, lower_is_better: bool = False
) -> ComparisonMetric:
    """Compare a single metric between two runs.

    Args:
        name: Metric name.
        val_a: Value from run A.
        val_b: Value from run B.
        lower_is_better: If True, lower values win (e.g., latency, hallucination rate).
    """
    winner = None
    if val_a is not None and val_b is not None:
        if abs(val_a - val_b) < COMPARISON_TIE_THRESHOLD:
            winner = "tie"
        elif lower_is_better:
            winner = "run_a" if val_a < val_b else "run_b"
        else:
            winner = "run_a" if val_a > val_b else "run_b"
    return ComparisonMetric(metric=name, run_a=val_a, run_b=val_b, winner=winner)


@router.get("/compare", response_model=ComparisonResponse)
async def compare_eval_runs(
    run_a_id: int,
    run_b_id: int,
    session: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Compare two evaluation runs side-by-side.

    Returns aggregate metric comparison and per-question breakdown.
    Questions are matched by text across both runs.
    """
    run_a = await session.get(EvalRun, run_a_id)
    run_b = await session.get(EvalRun, run_b_id)
    if not run_a:
        raise HTTPException(status_code=404, detail=f"Evaluation run {run_a_id} not found")
    if not run_b:
        raise HTTPException(status_code=404, detail=f"Evaluation run {run_b_id} not found")

    metrics = [
        _compare_metric("groundedness", run_a.avg_groundedness, run_b.avg_groundedness),
        _compare_metric("relevancy", run_a.avg_relevancy, run_b.avg_relevancy),
        _compare_metric(
            "context_precision", run_a.avg_context_precision, run_b.avg_context_precision
        ),
        _compare_metric(
            "context_relevancy", run_a.avg_context_relevancy, run_b.avg_context_relevancy
        ),
        _compare_metric("completeness", run_a.avg_completeness, run_b.avg_completeness),
        _compare_metric("correctness", run_a.avg_correctness, run_b.avg_correctness),
        _compare_metric(
            "compliance_accuracy", run_a.avg_compliance_accuracy, run_b.avg_compliance_accuracy
        ),
        _compare_metric("abstention", run_a.avg_abstention, run_b.avg_abstention),
        _compare_metric(
            "hallucination_rate",
            run_a.hallucination_rate,
            run_b.hallucination_rate,
            lower_is_better=True,
        ),
        _compare_metric(
            "latency_ms", run_a.avg_latency_ms, run_b.avg_latency_ms, lower_is_better=True
        ),
    ]

    results_a = await session.execute(
        select(EvalResult).where(EvalResult.eval_run_id == run_a_id).order_by(EvalResult.id)
    )
    results_b = await session.execute(
        select(EvalResult).where(EvalResult.eval_run_id == run_b_id).order_by(EvalResult.id)
    )

    a_by_question = {r.question: r for r in results_a.scalars().all()}
    b_by_question = {r.question: r for r in results_b.scalars().all()}

    all_questions = list(
        dict.fromkeys(list(a_by_question.keys()) + list(b_by_question.keys()))
    )

    questions = [
        QuestionComparison(
            question=q,
            run_a=_build_result_response(a_by_question[q]) if q in a_by_question else None,
            run_b=_build_result_response(b_by_question[q]) if q in b_by_question else None,
        )
        for q in all_questions
    ]

    return ComparisonResponse(
        run_a=_build_run_response(run_a),
        run_b=_build_run_response(run_b),
        metrics=metrics,
        questions=questions,
    )


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

    base_response = _build_run_response(run)
    return EvalRunDetailResponse(
        **base_response.model_dump(),
        results=[_build_result_response(r) for r in result_rows],
    )


@router.post("/{eval_run_id}/rerun", response_model=EvalRunCreateResponse, status_code=201)
async def rerun_eval(
    eval_run_id: int,
    request: EvalRunRerun,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> EvalRunCreateResponse:
    """Re-run an evaluation with a different model.

    Copies the questions from an existing run and creates a new run
    using the specified model. Useful for comparing a new model against
    previously evaluated results without re-entering questions.
    """
    original_run = await session.get(EvalRun, eval_run_id)
    if not original_run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    results = await session.execute(
        select(EvalResult.question)
        .where(EvalResult.eval_run_id == eval_run_id)
        .order_by(EvalResult.id)
    )
    questions = [EvalQuestion(question=row[0]) for row in results.all()]
    if not questions:
        raise HTTPException(
            status_code=400, detail="Original run has no questions to re-run"
        )

    run = EvalRun(
        model_name=request.model_name,
        question_set_id=original_run.question_set_id,
        status="pending",
        total_questions=len(questions),
    )
    session.add(run)
    await session.flush()

    run_id = run.id
    run_model = run.model_name
    run_status = run.status
    run_total = run.total_questions

    background_tasks.add_task(
        _run_evaluation,
        eval_run_id=run_id,
        model_name=request.model_name,
        questions=questions,
    )

    await session.commit()

    return EvalRunCreateResponse(
        eval_run_id=run_id,
        model_name=run_model,
        status=run_status,
        total_questions=run_total,
        message=f"Re-run started with {len(questions)} questions from run #{eval_run_id}",
    )
