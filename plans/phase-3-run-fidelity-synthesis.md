# Phase 3: Run Fidelity and Synthesis Quality

## Goal

Make evaluation runs fully reproducible by capturing all configuration
that influenced results. Improve question synthesis so it samples the
corpus fairly instead of biasing toward early documents.

## Why This Phase

**Run fidelity**: When comparing two runs from different dates, you
currently cannot tell whether results changed because of model
differences or because retrieval config / judge model / corpus changed
between runs. Capturing this metadata makes comparisons trustworthy.

**Synthesis quality**: The current synthesizer (`synthesizer.py:98-99`)
selects chunks with `query.order_by(Chunk.id).limit(50)`, which strongly
biases toward the first document ingested. If truth is generated from a
narrow slice of the corpus, evaluation is also narrow.

## Current State

**Run metadata gaps** -- `EvalRun` stores:
- model_name, profile_id, profile_version (good)
- Missing: judge_model_name, retrieval_config_snapshot, corpus_snapshot
  (document IDs + chunk counts at run time), synthesis_model_name

**Synthesis bias** -- `generate_questions()`:
- Selects chunks ordered by `Chunk.id` (insertion order)
- Limited to first 50 chunks (`MAX_CONTEXTS`)
- No document balancing -- if doc A has 100 chunks and doc B has 20,
  doc A dominates the synthesis context
- No section diversity -- questions cluster around whatever the first
  50 chunks cover

## Depends On

Phase 1 (Structured Truth) -- synthesis improvements generate richer
truth payloads.

This phase runs in parallel with Phase 2. No dependency between them.

## Work Items

### 3A. Capture Run Metadata

**Files to modify:**
- `packages/db/src/db/models.py` -- Add columns to `EvalRun`:
  - `judge_model_name: String(200)` -- which model scored this run
  - `retrieval_config: JSON` -- snapshot of retrieval params used
  - `corpus_snapshot: JSON` -- document IDs and chunk counts at run time
  - `synthesis_model_name: String(200)` -- model used for question generation
    (if questions were synthesized)
- `packages/db/alembic/` -- New migration
- `packages/api/src/routes/evaluation.py` -- Capture these values when
  creating/running an eval run:
  - `judge_model_name` from `settings.resolved_judge_model_name`
  - `retrieval_config` from the profile's retrieval settings
  - `corpus_snapshot` by querying Document table for current state
- `packages/api/src/schemas/evaluation.py` -- Add fields to
  `EvalRunResponse` and `EvalRunDetailResponse`

**What changes:**
- Every eval run records exactly what configuration was in effect
- Comparison endpoint can warn when comparing runs with different
  judge models or retrieval configs
- UI (Phase 4) can display this metadata

### 3B. Add Comparison Metadata Warnings

**Files to modify:**
- `packages/api/src/routes/evaluation.py` -- `compare_eval_runs()` adds
  warnings for:
  - Different judge models
  - Different retrieval configs
  - Different corpus snapshots (documents added/removed between runs)

**What changes:**
- New warning codes: `JUDGE_MODEL_MISMATCH`, `RETRIEVAL_CONFIG_MISMATCH`,
  `CORPUS_CHANGED`
- These join existing warnings (PROFILE_MISMATCH, QUESTION_SET_MISMATCH)

### 3C. Document-Balanced Synthesis

**Files to modify:**
- `packages/api/src/services/synthesizer.py` -- Replace `ORDER BY Chunk.id
  LIMIT 50` with balanced sampling:
  1. Count chunks per document
  2. Allocate chunk budget per document proportionally (or equally)
  3. Sample chunks from each document, preferring diversity of sections
  4. Build synthesis context from balanced selection

**Algorithm:**
```python
# Instead of: SELECT text FROM chunk ORDER BY id LIMIT 50
# Do:
# 1. Get all ready documents
# 2. Allocate MAX_CONTEXTS / len(documents) chunks per doc (min 2)
# 3. For each doc, select chunks spread across pages/sections
# 4. Combine into synthesis context
```

**What changes:**
- Questions cover the full corpus, not just the first document
- Each document contributes proportionally to question generation
- Section diversity within each document (spread across pages)
- `truth_metadata.source_chunk_ids` correctly reflects which chunks
  informed each question

### 3D. Source Traceability for Generated Truth

**Files to modify:**
- `packages/api/src/services/synthesizer.py` -- When generating questions,
  track which chunks were in the synthesis context and record them in
  `truth_metadata.source_chunk_ids`
- Pass source document filenames into `truth.required_documents`

**What changes:**
- Each generated question's truth payload includes:
  - `source_chunk_ids`: IDs of chunks that were in the synthesis context
  - `required_documents`: filenames of documents referenced in the
    expected answer
- This creates a traceable chain: document -> chunks -> question -> truth

## Exit Conditions

```bash
# Lint and format pass
cd packages/api && uv run ruff check src/ && uv run ruff format --check src/

# All tests pass
cd packages/api && uv run pytest

# New tests pass: run metadata capture, balanced synthesis,
# comparison metadata warnings
cd packages/api && uv run pytest tests/test_run_metadata.py -v
cd packages/api && uv run pytest tests/test_synthesizer.py -v

# Migration applies cleanly
cd packages/db && uv run alembic upgrade head
```

## What This Phase Does NOT Include

- UI display of run metadata (Phase 4)
- Version tracking for truth sets (Phase 5)
- Experiment history or regression analysis (Phase 5)

## Estimated PR Size

~400-500 lines of changed code (excluding tests). Split into two PRs:
- PR 3A: Run metadata capture + comparison warnings (~250 lines)
- PR 3B: Balanced synthesis + source traceability (~250 lines)

## Review Gate

Before Phase 4 begins:
- Code review (code-reviewer agent)
- Test review -- verify synthesis balance across documents, metadata
  capture completeness
- Verify backward compatibility with existing runs (null metadata OK)
