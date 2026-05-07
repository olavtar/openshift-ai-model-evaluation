# Phase 2: Deterministic Evaluation Layer

## Goal

Add rule-based evaluation checks that do not require an LLM judge call.
These checks are cheaper, faster, more stable, and more explainable than
judge-based scoring. Formalize the split between retrieval quality and
answer quality evaluation.

## Why This Phase

The current pipeline runs 4-8 LLM judge calls per question. Some checks
can be made deterministic:
- "Were the required documents retrieved?" -- string matching
- "Were the expected chunks found?" -- already done (`compute_chunk_alignment`)
- "Did the model answer when it should have abstained?" -- keyword heuristics
- "Does the answer reference sources not in the retrieval context?" --
  cross-reference check

These checks are binary (pass/fail) and do not need LLM interpretation.

## Current State

- `compute_chunk_alignment()` in `scoring.py:224-267` is the only
  deterministic check
- Coverage gap classification (`coverage.py:336-343`) classifies failures
  as retrieval vs generation, but uses LLM for concept extraction
- Verdicts apply profile thresholds but all thresholds are on LLM-scored
  metrics
- No deterministic validation of retrieval quality independent of LLM judge

## Depends On

Phase 1 (Structured Truth) -- `truth.answer_truth` (required_concepts,
abstention_expected) and `truth.retrieval_truth` (required_documents,
expected_chunk_refs) must exist.

## Work Items

### 2A. Create Deterministic Check Service

**New file:**
- `packages/api/src/services/deterministic_checks.py`

**What it does:**

```python
@dataclass
class DeterministicCheckResult:
    check_name: str        # e.g. "document_presence"
    passed: bool
    detail: str            # human-readable explanation
    category: str          # "retrieval" or "generation"

async def run_deterministic_checks(
    truth: TruthPayload,
    retrieved_chunks: list[dict],
    answer: str,
    contexts: list[str],
) -> list[DeterministicCheckResult]:
```

**Checks to implement:**

1. **Document Presence** (retrieval check)
   - Are all `truth.retrieval_truth.required_documents` represented in
     retrieved chunks?
   - Compare against `chunk["source_document"]` values
   - Category: retrieval

2. **Chunk Alignment** (retrieval check)
   - Move existing `compute_chunk_alignment()` logic here
   - Uses `truth.retrieval_truth.expected_chunk_refs` (resolve `chunk:{id}`
     refs to chunk IDs)
   - Category: retrieval

3. **Abstention Validation** (generation check)
   - When `truth.answer_truth.abstention_expected` is true, check if
     answer contains abstention signals ("I don't have enough information",
     "the provided context does not", etc.)
   - When `truth.answer_truth.abstention_expected` is false, check answer
     is not an unnecessary abstention
   - Category: generation

4. **Unsupported Source Reference** (generation check)
   - Check if the answer references document names or sources not
     present in the retrieval context
   - Category: generation

### 2B. Integrate Deterministic Checks into Pipeline

**Files to modify:**
- `packages/api/src/routes/evaluation.py` -- `_process_question()` calls
  deterministic checks after retrieval and generation, before LLM scoring
- `packages/db/src/db/models.py` -- Add `deterministic_checks` JSON column
  to `EvalResult` for storing check results
- `packages/db/alembic/` -- New migration for the column
- `packages/api/src/schemas/evaluation.py` -- Add deterministic check
  results to `EvalResultResponse`

**What changes:**
- Deterministic checks run first (fast, no LLM cost)
- Results stored as JSON on `EvalResult.deterministic_checks`
- If critical deterministic checks fail, LLM scoring still runs (for
  completeness) but the question verdict reflects the deterministic
  failure

### 2C. Enrich Verdicts with Deterministic Results

**Files to modify:**
- `packages/api/src/services/verdicts.py` -- `compute_question_verdict()`
  accepts deterministic check results alongside metric scores
- `packages/api/src/services/profiles.py` -- Add optional
  `deterministic_gates` to `EvalProfile` for profile-driven deterministic
  requirements

**What changes:**
- Verdict logic considers deterministic checks:
  - Failed retrieval checks -> FAIL with reason `FAIL_RETRIEVAL_INCOMPLETE`
  - Failed abstention check -> FAIL with reason `FAIL_ABSTENTION_VIOLATION`
  - Failed source reference check -> FAIL with reason
    `FAIL_UNSUPPORTED_SOURCE_REFERENCE`
- Profiles can specify which deterministic checks are critical vs warning
- `QuestionVerdict` dataclass includes `deterministic_results` field

### 2D. Update Comparison to Include Deterministic Results

**Files to modify:**
- `packages/api/src/routes/evaluation.py` -- `compare_eval_runs()` includes
  deterministic check pass rates in comparison metrics
- `packages/api/src/schemas/evaluation.py` -- `ComparisonMetric` can represent
  deterministic check metrics

**What changes:**
- Comparison includes aggregate deterministic check pass rates
- Per-question comparison shows deterministic check results for both models
- Decision logic uses deterministic check pass rates as an additional
  comparison dimension

## Exit Conditions

```bash
# Lint and format pass
cd packages/api && uv run ruff check src/ && uv run ruff format --check src/

# All existing tests still pass
cd packages/api && uv run pytest

# New tests pass: deterministic checks, verdict integration,
# comparison with deterministic results
cd packages/api && uv run pytest tests/test_deterministic_checks.py -v

# Migration applies cleanly
cd packages/db && uv run alembic upgrade head
```

## What This Phase Does NOT Include

- UI display of deterministic check results (Phase 4)
- Embedding-based concept matching (deferred -- current keyword heuristic
  is sufficient for PoC/MVP)
- Run metadata capture (Phase 3)

## Estimated PR Size

~500-600 lines of changed code (excluding tests). Split into two PRs:
- PR 2A: Deterministic check service + DB column + pipeline integration
  (~350 lines)
- PR 2B: Verdict enrichment + comparison integration + profile gates
  (~250 lines)

## Review Gate

Before Phase 4 begins (Phase 3 can proceed in parallel):
- Code review (code-reviewer agent) -- deterministic check logic
- Security review (security-engineer agent) -- input handling in checks
- Test review -- check coverage of each deterministic check type
- Verify backward compatibility with runs that have no deterministic data
