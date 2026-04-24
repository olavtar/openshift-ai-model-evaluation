# This project was developed with assistance from AI tools.
"""Tests for deterministic retrieval checks."""

from src.schemas.truth import AnswerTruth, RetrievalTruth, TruthMetadata, TruthPayload
from src.services.deterministic_checks import (
    check_chunk_alignment,
    check_document_presence,
    run_deterministic_checks,
)


def _make_truth(
    required_documents: list[str] | None = None,
    expected_chunk_refs: list[str] | None = None,
    evidence_mode: str = "traced_from_synthesis",
) -> TruthPayload:
    """Build a TruthPayload for testing."""
    return TruthPayload(
        answer_truth=AnswerTruth(required_concepts=["concept"]),
        retrieval_truth=RetrievalTruth(
            required_documents=required_documents or [],
            expected_chunk_refs=expected_chunk_refs or [],
            evidence_mode=evidence_mode,
        ),
        metadata=TruthMetadata(
            generated_by_model="test-model",
            generated_at="2026-01-01T00:00:00",
        ),
    )


def _make_chunks(docs_and_ids: list[tuple[str, int]]) -> list[dict]:
    """Build chunk dicts from (source_document, id) pairs."""
    return [
        {"id": cid, "source_document": doc, "text": f"Chunk {cid}"} for doc, cid in docs_and_ids
    ]


# --- Document Presence ---


def test_document_presence_all_found():
    """Should pass when all required documents are in retrieved chunks."""
    truth = _make_truth(required_documents=["report.pdf", "guide.pdf"])
    chunks = _make_chunks([("report.pdf", 1), ("guide.pdf", 2), ("extra.pdf", 3)])
    result = check_document_presence(truth, chunks)
    assert result.passed
    assert result.category == "retrieval"


def test_document_presence_missing():
    """Should fail when required documents are missing from retrieval."""
    truth = _make_truth(required_documents=["report.pdf", "guide.pdf"])
    chunks = _make_chunks([("report.pdf", 1)])
    result = check_document_presence(truth, chunks)
    assert not result.passed
    assert "guide.pdf" in result.detail


def test_document_presence_no_requirements():
    """Should pass when no required documents are specified."""
    truth = _make_truth(required_documents=[])
    result = check_document_presence(truth, [])
    assert result.passed


def test_document_presence_all_missing():
    """Should fail and list all missing documents."""
    truth = _make_truth(required_documents=["report.pdf", "guide.pdf"])
    chunks = _make_chunks([("unrelated.pdf", 99)])
    result = check_document_presence(truth, chunks)
    assert not result.passed
    assert "2/2" in result.detail


# --- Chunk Alignment ---


def test_chunk_alignment_all_found():
    """Should pass when all expected chunks are retrieved."""
    truth = _make_truth(expected_chunk_refs=["chunk:1", "chunk:2"])
    chunks = _make_chunks([("doc.pdf", 1), ("doc.pdf", 2), ("doc.pdf", 3)])
    result = check_chunk_alignment(truth, chunks)
    assert result.passed
    assert "2/2" in result.detail


def test_chunk_alignment_partial_below_threshold():
    """Should fail when fewer than half of expected chunks are retrieved."""
    truth = _make_truth(expected_chunk_refs=["chunk:1", "chunk:2", "chunk:3", "chunk:4"])
    chunks = _make_chunks([("doc.pdf", 1)])
    result = check_chunk_alignment(truth, chunks)
    assert not result.passed
    assert "1/4" in result.detail


def test_chunk_alignment_half_passes():
    """Should pass when exactly half of expected chunks are retrieved."""
    truth = _make_truth(expected_chunk_refs=["chunk:1", "chunk:2"])
    chunks = _make_chunks([("doc.pdf", 1)])
    result = check_chunk_alignment(truth, chunks)
    assert result.passed
    assert "1/2" in result.detail


def test_chunk_alignment_no_requirements():
    """Should pass when no expected chunk refs are specified."""
    truth = _make_truth(expected_chunk_refs=[])
    result = check_chunk_alignment(truth, [])
    assert result.passed


def test_chunk_alignment_none_found():
    """Should fail when none of the expected chunks are retrieved."""
    truth = _make_truth(expected_chunk_refs=["chunk:10", "chunk:20"])
    chunks = _make_chunks([("doc.pdf", 1), ("doc.pdf", 2)])
    result = check_chunk_alignment(truth, chunks)
    assert not result.passed
    assert "0/2" in result.detail


# --- run_deterministic_checks ---


def test_run_checks_returns_two_retrieval_checks():
    """Should run document_presence and chunk_alignment checks."""
    truth = _make_truth(
        required_documents=["report.pdf"],
        expected_chunk_refs=["chunk:1"],
    )
    chunks = _make_chunks([("report.pdf", 1)])
    results = run_deterministic_checks(truth, chunks)
    assert len(results) == 2
    check_names = {r["check_name"] for r in results}
    assert check_names == {"document_presence", "chunk_alignment"}
    assert all(r["category"] == "retrieval" for r in results)
    assert all(isinstance(r["passed"], bool) for r in results)


def test_run_checks_without_truth():
    """Should return empty list when no truth is available."""
    results = run_deterministic_checks(None, [])
    assert results == []


def test_run_checks_all_pass():
    """Should have all checks pass with matching truth and retrieval."""
    truth = _make_truth(
        required_documents=["report.pdf"],
        expected_chunk_refs=["chunk:1"],
    )
    chunks = _make_chunks([("report.pdf", 1)])
    results = run_deterministic_checks(truth, chunks)
    assert all(r["passed"] for r in results)


def test_run_checks_both_fail():
    """Should detect retrieval failures when docs and chunks are missing."""
    truth = _make_truth(
        required_documents=["report.pdf", "guide.pdf"],
        expected_chunk_refs=["chunk:1", "chunk:2", "chunk:3"],
    )
    chunks = _make_chunks([("extra.pdf", 99)])
    results = run_deterministic_checks(truth, chunks)
    assert len(results) == 2
    assert not any(r["passed"] for r in results)
