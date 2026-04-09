# This project was developed with assistance from AI tools.
"""Business verdict layer -- applies profile thresholds to raw metric scores.

All pass/fail logic lives here. The scoring layer (scoring.py) produces raw
scores only (threshold=0.0). This module applies profile-defined thresholds
to produce PASS/FAIL/REVIEW_REQUIRED verdicts with specific fail reasons.
"""

from dataclasses import dataclass, field

from .profiles import EvalProfile


@dataclass
class QuestionVerdict:
    """Verdict for a single evaluation question."""

    verdict: str  # PASS | FAIL | REVIEW_REQUIRED
    fail_reasons: list[str] = field(default_factory=list)
    passed_metrics: list[str] = field(default_factory=list)
    failed_metrics: list[str] = field(default_factory=list)


@dataclass
class RunVerdict:
    """Aggregate verdict for an evaluation run."""

    overall: str  # PASS | FAIL | REVIEW_REQUIRED
    pass_count: int = 0
    fail_count: int = 0
    review_count: int = 0
    total: int = 0
    summary: str = ""


_FAIL_REASON_MAP = {
    "groundedness_score": "FAIL_LOW_GROUNDEDNESS",
    "relevancy_score": "FAIL_LOW_RELEVANCY",
    "context_precision_score": "FAIL_LOW_CONTEXT_PRECISION",
    "context_relevancy_score": "FAIL_LOW_CONTEXT_RELEVANCY",
    "completeness_score": "FAIL_INSUFFICIENT_COVERAGE",
    "correctness_score": "FAIL_UNSUPPORTED_CLAIM",
    "compliance_accuracy_score": "FAIL_COMPLIANCE_VIOLATION",
    "abstention_score": "FAIL_CONFIDENT_WITHOUT_CONTEXT",
}


def compute_question_verdict(
    scores: dict[str, float | None],
    profile: EvalProfile,
) -> QuestionVerdict:
    """Apply profile thresholds to metric scores and produce a verdict.

    Logic:
    - If any metric is below its critical_threshold -> FAIL
    - If any metric is below its regular threshold -> REVIEW_REQUIRED
    - If all pass -> PASS
    - Metrics with None scores are skipped (not penalized).

    Args:
        scores: Dict of metric_name -> score (from score_result()).
        profile: The evaluation profile with thresholds.

    Returns:
        QuestionVerdict with verdict, fail_reasons, and metric lists.
    """
    has_critical_fail = False
    has_threshold_fail = False
    fail_reasons: list[str] = []
    passed_metrics: list[str] = []
    failed_metrics: list[str] = []

    # Check critical thresholds first
    for metric_key, critical_threshold in profile.critical_thresholds.items():
        score = scores.get(metric_key)
        if score is None:
            continue
        if score < critical_threshold:
            has_critical_fail = True
            reason = _FAIL_REASON_MAP.get(metric_key, f"FAIL_{metric_key.upper()}")
            fail_reasons.append(reason)
            failed_metrics.append(metric_key)

    # Check regular thresholds
    for metric_key, threshold in profile.thresholds.items():
        score = scores.get(metric_key)
        if score is None:
            continue
        if metric_key in failed_metrics:
            continue  # Already counted as critical fail
        if score < threshold:
            has_threshold_fail = True
            reason = _FAIL_REASON_MAP.get(metric_key, f"FAIL_{metric_key.upper()}")
            fail_reasons.append(reason)
            failed_metrics.append(metric_key)
        else:
            passed_metrics.append(metric_key)

    if has_critical_fail:
        verdict = "FAIL"
    elif has_threshold_fail:
        verdict = "REVIEW_REQUIRED"
    else:
        verdict = "PASS"

    return QuestionVerdict(
        verdict=verdict,
        fail_reasons=fail_reasons,
        passed_metrics=passed_metrics,
        failed_metrics=failed_metrics,
    )


def compute_run_verdict(question_verdicts: list[QuestionVerdict]) -> RunVerdict:
    """Aggregate question verdicts into a run-level verdict.

    Args:
        question_verdicts: List of per-question verdicts.

    Returns:
        RunVerdict with counts and overall verdict.
    """
    total = len(question_verdicts)
    pass_count = sum(1 for v in question_verdicts if v.verdict == "PASS")
    fail_count = sum(1 for v in question_verdicts if v.verdict == "FAIL")
    review_count = sum(1 for v in question_verdicts if v.verdict == "REVIEW_REQUIRED")

    if fail_count > 0:
        overall = "FAIL"
    elif review_count > 0:
        overall = "REVIEW_REQUIRED"
    else:
        overall = "PASS"

    summary = f"{pass_count}/{total} questions passed all criteria"

    return RunVerdict(
        overall=overall,
        pass_count=pass_count,
        fail_count=fail_count,
        review_count=review_count,
        total=total,
        summary=summary,
    )
