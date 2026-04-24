# This project was developed with assistance from AI tools.
"""Deterministic evaluation checks -- rule-based, no LLM judge required.

These checks validate retrieval quality and answer quality using string
matching and heuristics against structured truth payloads. They are
cheaper, faster, more stable, and more explainable than judge-based scoring.

Retrieval checks (document_presence, chunk_alignment) are strong gate
candidates. Generation checks (abstention_validation, source_reference)
are heuristic and stored as warnings initially.
"""

import logging
import re
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


# Abstention signal phrases (case-insensitive matching)
_ABSTENTION_SIGNALS = [
    "i don't have enough information",
    "i do not have enough information",
    "the provided context does not",
    "the context does not contain",
    "insufficient information",
    "cannot answer",
    "unable to answer",
    "not enough context",
    "no relevant information",
    "does not address",
    "not mentioned in",
    "not covered in the provided",
    "i cannot determine",
    "based on the available context, i cannot",
]


def _contains_abstention(text: str) -> bool:
    """Check if text contains abstention signal phrases."""
    lower = text.lower()
    return any(signal in lower for signal in _ABSTENTION_SIGNALS)


def check_abstention(
    truth: TruthPayload,
    answer: str,
) -> CheckResult:
    """Validate abstention behavior against truth expectations.

    When abstention is expected, the answer should contain abstention signals.
    When abstention is not expected, the answer should be substantive.

    Args:
        truth: Structured truth payload with abstention expectation.
        answer: Model-generated answer text.

    Returns:
        CheckResult indicating whether abstention behavior matches expectation.
    """
    expected = truth.answer_truth.abstention_expected
    has_abstention = _contains_abstention(answer)

    if expected and not has_abstention:
        return CheckResult(
            check_name="abstention_validation",
            passed=False,
            detail="Model answered when it should have abstained",
            category="generation",
        )
    if not expected and has_abstention:
        return CheckResult(
            check_name="abstention_validation",
            passed=False,
            detail="Model abstained when it should have answered",
            category="generation",
        )
    return CheckResult(
        check_name="abstention_validation",
        passed=True,
        detail="Abstention behavior matches expectation",
        category="generation",
    )


def check_source_reference(
    answer: str,
    retrieved_chunks: list[dict],
) -> CheckResult:
    """Check if the answer references documents not present in retrieval context.

    Looks for filename-like patterns in the answer and verifies they appear
    in the retrieved chunk source documents.

    Args:
        answer: Model-generated answer text.
        retrieved_chunks: Chunks from retrieval pipeline.

    Returns:
        CheckResult indicating whether all referenced sources are supported.
    """
    file_pattern = re.compile(r"\b([\w\-]+\.(?:pdf|docx?|txt|csv|xlsx?))\b", re.IGNORECASE)
    referenced_files = set(file_pattern.findall(answer))

    if not referenced_files:
        return CheckResult(
            check_name="source_reference",
            passed=True,
            detail="No document references found in answer",
            category="generation",
        )

    context_docs = {c.get("source_document", "") for c in retrieved_chunks}
    unsupported = [f for f in referenced_files if f not in context_docs]

    if unsupported:
        return CheckResult(
            check_name="source_reference",
            passed=False,
            detail=f"Answer references documents not in context: {unsupported}",
            category="generation",
        )
    return CheckResult(
        check_name="source_reference",
        passed=True,
        detail=f"All {len(referenced_files)} document references are supported by context",
        category="generation",
    )


def run_deterministic_checks(
    truth: TruthPayload | None,
    retrieved_chunks: list[dict],
    answer: str | None = None,
) -> list[dict]:
    """Run deterministic checks and return results as serializable dicts.

    Retrieval checks (document_presence, chunk_alignment) always run when
    truth is available. Generation checks (abstention_validation,
    source_reference) run when an answer is also provided.

    Args:
        truth: Structured truth payload (may be None for questions without truth).
        retrieved_chunks: Chunks from retrieval pipeline.
        answer: Model-generated answer text (optional; enables generation checks).

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

    if answer:
        results.append(check_abstention(truth, answer))
        results.append(check_source_reference(answer, retrieved_chunks))

    return [asdict(r) for r in results]
