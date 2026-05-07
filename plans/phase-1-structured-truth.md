# Phase 1: Structured Truth Foundation

## Goal

Make truth a first-class, structured, persistent, and frozen object. Every
question with an expected answer gets a structured truth payload attached
at creation time. This truth is immutable once created and serves as the
stable reference for all subsequent evaluations.

## Why This Comes First

Everything downstream depends on structured truth:
- Deterministic checks need `required_documents` and `expected_chunk_refs`
  to validate retrieval quality
- The retrieval/answer truth split needs formal separation at the schema level
- UI explainability needs structured data to display
- Versioning needs a stable truth schema to version

## Current State

- `QuestionSet.questions` is a JSON column storing `[{question, expected_answer}]`
- `expected_answer` is a plain text string -- no structure
- `EvalResult.expected_answer` copies this string per result
- Coverage analysis (`coverage.py`) extracts concepts from expected_answer
  at evaluation time using an LLM call (cached in-memory per session)
- `EvalQuestion` schema accepts optional `expected_chunks` list

## Target State

Each question with an expected answer includes a structured truth object
with two distinct concerns: what the answer must contain (`answer_truth`)
and what evidence should support it (`retrieval_truth`).

### Synthesis path example

```json
{
  "question": "What are the SEC filing requirements for ETFs?",
  "expected_answer": "ETFs must file Form N-1A and provide required prospectus disclosures...",
  "truth": {
    "answer_truth": {
      "required_concepts": [
        "ETF must file Form N-1A",
        "Prospectus disclosures are required",
        "Fees must be disclosed",
        "Risks must be disclosed",
        "Investment objectives must be disclosed"
      ],
      "abstention_expected": false
    },
    "retrieval_truth": {
      "required_documents": ["sec-etf-guide.pdf", "form-n1a-instructions.pdf"],
      "expected_chunk_refs": ["chunk:42", "chunk:43", "chunk:67"],
      "evidence_mode": "traced_from_synthesis"
    },
    "metadata": {
      "truth_schema_version": "1.0",
      "concept_extraction_version": "v1",
      "evidence_alignment_version": "v1",
      "generated_by_model": "mistral-small-24b",
      "generated_at": "2026-04-23T12:00:00Z",
      "source_chunk_ids": [42, 43, 67]
    }
  }
}
```

### Manual question with expected answer example

Same shape, different `evidence_mode`:

```json
{
  "question": "What registration forms do ETFs need?",
  "expected_answer": "ETFs register under the Investment Company Act using Form N-1A...",
  "truth": {
    "answer_truth": {
      "required_concepts": [
        "ETFs register under the Investment Company Act",
        "Form N-1A is the registration form"
      ],
      "abstention_expected": false
    },
    "retrieval_truth": {
      "required_documents": ["sec-etf-guide.pdf"],
      "expected_chunk_refs": ["chunk:12", "chunk:19"],
      "evidence_mode": "grounded_from_manual_answer"
    },
    "metadata": {
      "truth_schema_version": "1.0",
      "concept_extraction_version": "v1",
      "evidence_alignment_version": "v1",
      "generated_by_model": "mistral-small-24b",
      "generated_at": "2026-04-23T12:00:00Z",
      "source_chunk_ids": [12, 19]
    }
  }
}
```

## Why answer_truth and retrieval_truth Are Separate

The flat structure in the earlier draft mixed "what should the answer
contain" with "what evidence should be retrieved" -- two fundamentally
different concerns:

- `answer_truth` is checked by coverage analysis and the completeness/
  correctness GEval metrics. It answers: "Did the model say the right
  things?"
- `retrieval_truth` is checked by deterministic retrieval checks (Phase 2)
  and chunk alignment scoring. It answers: "Did the system find the right
  evidence?"

Separating them at the schema level means downstream code reads from the
right section without ambiguity: `coverage.py` reads `answer_truth`,
deterministic checks read `retrieval_truth`.

## Truth Generation by Entry Path

Truth is generated for **all** questions that have an expected answer,
regardless of how they entered the system. Both paths produce the same
top-level truth shape.

| Entry path | expected_answer | Truth generated? | answer_truth | retrieval_truth |
|------------|----------------|-----------------|--------------|-----------------|
| Synthesis | Yes (LLM-generated) | Full | Concepts extracted from expected answer | Traced from the chunks used during synthesis. `evidence_mode = "traced_from_synthesis"` |
| Manual + expected answer | Yes (user-provided) | Full | Concepts extracted from expected answer | Grounded by running expected answer through retrieval against the uploaded corpus. `evidence_mode = "grounded_from_manual_answer"` |
| Manual, no expected answer | No | No truth | -- | -- |
| Rerun | Inherited | Inherited | Same frozen truth as original run | Same frozen truth as original run |

The key difference between synthesis and manual is **how retrieval truth
is produced**, not **whether it exists**:

- **Synthesis**: The synthesizer knows which chunks it read to generate
  the question. Retrieval truth is traced directly from those chunks.
- **Manual**: The system does not know what the user was looking at. So
  it grounds the expected answer against the uploaded corpus using the
  same retrieval pipeline (`retrieve_chunks()` in `retrieval.py`) that
  the evaluation itself uses. This finds the chunks that best match the
  expected answer text and records them as retrieval expectations.

Both paths end up with `required_documents`, `expected_chunk_refs`, and
`source_chunk_ids` populated. Manual questions are not partial by default.

**Model for truth generation**: Both paths use the **judge model**
(`resolved_judge_model_name`) for concept extraction. The judge model
defines what a "concept" is -- using a different model for synthesis
vs manual would produce inconsistent concept lists from the same
expected answer text. `metadata.generated_by_model` records which model
was used.

**Corpus grounding uses the evaluation retrieval path**: The manual
path's `ground_answer_to_corpus()` calls `retrieve_chunks()` from
`retrieval.py` with the same parameters (from the profile if selected).
This ensures retrieval truth reflects what the evaluation pipeline
would actually retrieve, not a different search method.

## Work Items

### 1A. Define Truth Schema Models

**Files to modify:**
- `packages/db/src/db/models.py` -- No schema change needed;
  `QuestionSet.questions` is already a JSON column. The structured truth
  lives inside the existing JSON.
- `packages/api/src/schemas/question_set.py` -- Add nested Pydantic
  models for the truth structure
- `packages/api/src/schemas/evaluation.py` -- Update `EvalQuestion` and
  `SynthesizedQuestion` to include optional `truth` field

**New Pydantic models:**

```python
class AnswerTruth(BaseModel):
    required_concepts: list[str]
    abstention_expected: bool = False

class RetrievalTruth(BaseModel):
    required_documents: list[str] = []
    expected_chunk_refs: list[str] = []  # "chunk:{id}" format
    evidence_mode: Literal["traced_from_synthesis", "grounded_from_manual_answer"]

class TruthMetadata(BaseModel):
    truth_schema_version: str = "1.0"
    concept_extraction_version: str = "v1"
    evidence_alignment_version: str = "v1"
    generated_by_model: str
    generated_at: datetime
    source_chunk_ids: list[int] = []

class TruthPayload(BaseModel):
    answer_truth: AnswerTruth
    retrieval_truth: RetrievalTruth
    metadata: TruthMetadata
```

Backward compatible: existing question sets without truth still work.

### 1B. Create Truth Generation Service

**New file:**
- `packages/api/src/services/truth_generation.py`

**Internal building blocks:**

- `extract_answer_truth(expected_answer, model_name) -> AnswerTruth` --
  Calls judge model to extract `required_concepts` from expected answer
  text. Reuses the concept extraction prompt from `coverage.py`
  (`EXTRACT_CONCEPTS_PROMPT`). Sets `abstention_expected=false`.

- `build_retrieval_truth_from_synthesis(source_chunks) -> RetrievalTruth` --
  Extracts `required_documents` from chunk metadata (source_document
  field), builds `expected_chunk_refs` as `chunk:{id}` strings, sets
  `evidence_mode = "traced_from_synthesis"`.

- `ground_answer_to_corpus(expected_answer, session, profile) -> RetrievalTruth` --
  Runs expected answer text through `retrieve_chunks()` (same retrieval
  pipeline as evaluation, same profile-driven parameters). Records
  matched chunks as `expected_chunk_refs`, their source documents as
  `required_documents`, sets
  `evidence_mode = "grounded_from_manual_answer"`.

- `build_truth_metadata(model_name, source_chunk_ids) -> TruthMetadata` --
  Captures model, timestamp, version fields, source chunk IDs.

**Composed public API:**

- `generate_truth_from_synthesis(expected_answer, source_chunks, model_name) -> TruthPayload` --
  Calls `extract_answer_truth()` + `build_retrieval_truth_from_synthesis()`
  + `build_truth_metadata()`. Used by the synthesizer.

- `generate_truth_from_manual_answer(expected_answer, session, model_name, profile) -> TruthPayload` --
  Calls `extract_answer_truth()` + `ground_answer_to_corpus()` +
  `build_truth_metadata()`. Used for manual questions with expected answers.

### 1C. Update Synthesizer to Generate Structured Truth

**Files to modify:**
- `packages/api/src/services/synthesizer.py` -- After generating
  questions, call `generate_truth_from_synthesis()` for each question.
  Track which source chunks contributed to each question.

**What changes:**
- `generate_questions()` returns truth payload with each question
- Source chunks are tracked per question for `metadata.source_chunk_ids`
- Document filenames extracted for `retrieval_truth.required_documents`
- `retrieval_truth.evidence_mode = "traced_from_synthesis"`

### 1D. Generate Truth for Manual Questions

**Files to modify:**
- `packages/api/src/routes/question_sets.py` -- When saving a question
  set, for any question that has an `expected_answer` but no `truth`,
  call `generate_truth_from_manual_answer()` to create full truth
  including corpus-grounded retrieval expectations
- `packages/api/src/routes/evaluation.py` -- When creating an eval run
  with inline questions that have expected answers but no truth, generate
  truth before starting the run

**What changes:**
- Every question with an expected answer gets full truth (answer + retrieval)
- Manual questions are grounded against the uploaded corpus, not left partial
- Truth generation is synchronous at save/creation time with a progress
  indicator in the UI. This keeps the invariant that truth is always
  present after save completes.
- The LLM call for concept extraction moves from eval-time (coverage.py)
  to creation-time (truth generation) -- evaluated once, used many times

### 1E. Wire Truth into Evaluation Pipeline

**Files to modify:**
- `packages/api/src/routes/evaluation.py` -- `_process_question()` reads
  truth from `EvalQuestion.truth` and passes relevant fields downstream
- `packages/api/src/services/coverage.py` -- `detect_coverage_gaps()`
  accepts pre-extracted concepts from `truth.answer_truth.required_concepts`,
  skipping the LLM extraction step
- `packages/api/src/services/scoring.py` -- `compute_chunk_alignment()`
  uses `truth.retrieval_truth.expected_chunk_refs` (parsing chunk IDs
  from the `chunk:{id}` format)

**What changes:**
- When truth is available, concept extraction is skipped (deterministic)
- When truth is not available (legacy data), existing LLM-based extraction
  still works as fallback
- `retrieval_truth` is available on the result for deterministic checks
  (Phase 2)
- Truth is frozen at creation time and never regenerated -- reruns of the
  same questions use the same truth

### 1F. Do Not Use filename:page as Canonical Chunk Key

The earlier draft used references like `"sec-etf-guide.pdf:3"` for
expected chunks. Chunk IDs are stable database keys; filenames can change
on re-upload and page numbers depend on parsing.

Use `chunk:{id}` (e.g., `"chunk:42"`) as the canonical stored reference.
Filenames and page numbers are derived for display from the chunk record.
The scoring pipeline resolves chunk refs by ID, not by filename matching.

## Exit Conditions

```bash
# Schema validation passes
cd packages/api && uv run ruff check src/ && uv run ruff format --check src/

# Existing tests still pass
cd packages/api && uv run pytest

# New tests pass: truth schema, truth generation (both paths),
# synthesis with truth, manual questions with corpus grounding,
# coverage with pre-extracted concepts
cd packages/api && uv run pytest tests/test_truth.py -v

# Type check passes
cd packages/ui && pnpm type-check
```

## What This Phase Does NOT Include

- Deterministic checks using truth fields (Phase 2)
- UI display of structured truth (Phase 4)
- Full version tracking and experiment history (Phase 5)

## Estimated PR Size

~500-600 lines of changed code (excluding tests). Split into two PRs:
- PR 1A: Truth schema models + truth generation service + pipeline
  wiring (~350 lines)
- PR 1B: Synthesizer truth generation + manual question corpus grounding
  (~250 lines)

## Review Gate

Before Phase 2 begins:
- Code review (code-reviewer agent)
- Security review (security-engineer agent) -- truth metadata handling
- Test review -- meaningful coverage of truth generation (both paths),
  corpus grounding, and freezing behavior
- Verify backward compatibility with existing question sets
