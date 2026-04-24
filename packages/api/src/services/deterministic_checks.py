# This project was developed with assistance from AI tools.
"""Deterministic evaluation checks -- rule-based, no LLM judge required.

These checks validate retrieval quality using string matching against
structured truth payloads. They are cheaper, faster, more stable, and
more explainable than judge-based scoring.

Phase 2A includes retrieval checks only (document_presence, chunk_alignment).
Generation checks (abstention, source reference) will be added in Phase 2B.
"""

import logging
from dataclasses import asdict, dataclass

from ..schemas.truth import TruthPayload

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single deterministic check."""

    check_name: str
    passed: bool
    detail: str
    category: str  # "retrieval" or "generation"


def check_document_presence(
    truth: TruthPayload,
    retrieved_chunks: list[dict],
) -> CheckResult:
    """Check if all required documents are represented in retrieved chunks.

    Args:
        truth: Structured truth payload with retrieval requirements.
        retrieved_chunks: Chunks from retrieval pipeline.

    Returns:
        CheckResult indicating whether all required documents were found.
    """
    required = truth.retrieval_truth.required_documents
    if not required:
        return CheckResult(
            check_name="document_presence",
            passed=True,
            detail="No required documents specified",
            category="retrieval",
        )

    retrieved_docs = {c.get("source_document", "") for c in retrieved_chunks}
    missing = [doc for doc in required if doc not in retrieved_docs]

    if missing:
        return CheckResult(
            check_name="document_presence",
            passed=False,
            detail=f"Missing {len(missing)}/{len(required)} required documents: {missing}",
            category="retrieval",
        )
    return CheckResult(
        check_name="document_presence",
        passed=True,
        detail=f"All {len(required)} required documents present",
        category="retrieval",
    )


def check_chunk_alignment(
    truth: TruthPayload,
    retrieved_chunks: list[dict],
) -> CheckResult:
    """Check if expected chunk references are found in retrieved chunks.

    Supports chunk:{id} canonical format from truth payloads. Legacy
    filename/page formats are handled by compute_chunk_alignment() in
    scoring.py for backward compatibility with old question data.

    Args:
        truth: Structured truth payload with chunk reference expectations.
        retrieved_chunks: Chunks from retrieval pipeline.

    Returns:
        CheckResult with pass/fail based on chunk recall (threshold: 50%).
    """
    expected_refs = truth.retrieval_truth.expected_chunk_refs
    if not expected_refs:
        return CheckResult(
            check_name="chunk_alignment",
            passed=True,
            detail="No expected chunk references specified",
            category="retrieval",
        )

    retrieved_ids: set[int] = set()
    for chunk in retrieved_chunks:
        if chunk.get("id") is not None:
            retrieved_ids.add(int(chunk["id"]))

    matched = 0
    for ref in expected_refs:
        if ref.startswith("chunk:"):
            try:
                chunk_id = int(ref[6:])
                if chunk_id in retrieved_ids:
                    matched += 1
            except ValueError:
                pass

    recall = matched / len(expected_refs) if expected_refs else 1.0
    passed = recall >= 0.5

    return CheckResult(
        check_name="chunk_alignment",
        passed=passed,
        detail=f"Chunk recall: {matched}/{len(expected_refs)} ({recall:.0%})",
        category="retrieval",
    )


def run_deterministic_checks(
    truth: TruthPayload | None,
    retrieved_chunks: list[dict],
) -> list[dict]:
    """Run retrieval deterministic checks and return results as serializable dicts.

    Args:
        truth: Structured truth payload (may be None for questions without truth).
        retrieved_chunks: Chunks from retrieval pipeline.

    Returns:
        List of check result dicts, each with check_name, passed, detail, category.
        Returns empty list if no truth is available.
    """
    if not truth:
        return []

    results = [
        check_document_presence(truth, retrieved_chunks),
        check_chunk_alignment(truth, retrieved_chunks),
    ]

    return [asdict(r) for r in results]
