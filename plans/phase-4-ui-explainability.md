# Phase 4: UI Explainability

## Goal

Surface all the structured truth, deterministic check results, retrieval
evidence, and run metadata in the UI so users can understand not just
what the scores are, but why a model passed or failed.

## Why This Phase

Phases 1-3 built a rich data model: structured truth, deterministic
checks, retrieval/generation failure classification, and run metadata.
But none of this is visible to users yet. The evaluation detail page
(`evaluations/$id.tsx`) shows metric scores and answers but not:
- What the system expected (required concepts, required documents)
- What was retrieved vs what was expected
- Whether failures are retrieval or generation problems
- Which checks were deterministic vs judge-based
- What configuration produced the run

This is where the architecture becomes useful to people, not just to
the backend.

## Current UI State

**Evaluation Detail Page** (`evaluations/$id.tsx`):
- Summary metrics grid (8 metrics)
- Verdict badge (PASS/FAIL/REVIEW_REQUIRED)
- Per-question expandable rows showing: question, answer, expected
  answer, metric scores, retrieved context chunks, error messages

**Comparison Page** (`evaluations/compare.tsx`):
- Executive verdict card with decision reasons
- Aggregate metric comparison (11 metrics)
- Per-question side-by-side with answers, scores, coverage gaps
- Warnings for profile/question set mismatches

## Depends On

Phases 1-3 must be complete. The UI displays data created in those phases.

## Work Items

### 4A. Truth and Evidence Display in Evaluation Detail

**Files to modify:**
- `packages/ui/src/routes/evaluations/$id.tsx` -- Add truth display
  section to expanded question results
- `packages/ui/src/schemas/evaluation.ts` -- Add Zod types for truth
  payload, deterministic check results, run metadata
- `packages/ui/src/services/evaluation.ts` -- No changes needed (data
  comes through existing API response)

**What to add to expanded question results:**

1. **Answer Truth Section** (collapsible, from `truth.answer_truth`)
   - Required concepts list (with covered/missing indicators from
     coverage analysis)
   - Abstention expected flag
   - Failure classification: retrieval failures vs generation failures

2. **Retrieval Truth Section** (collapsible, from `truth.retrieval_truth`)
   - Required documents list (with present/absent indicators from
     deterministic checks)
   - Expected chunk refs (with alignment score)
   - Evidence mode badge: "Traced from synthesis" or "Grounded from corpus"

3. **Deterministic Check Results** (pass/fail badges)
   - Document presence: pass/fail
   - Chunk alignment: score
   - Abstention validation: pass/fail
   - Unsupported source reference: pass/fail
   - Category labels: "Retrieval" vs "Generation"

### 4B. Enhanced Comparison View

**Files to modify:**
- `packages/ui/src/routes/evaluations/compare.tsx` -- Add new sections
  to comparison display
- `packages/ui/src/schemas/evaluation.ts` -- Add types for run metadata
  and deterministic comparison metrics

**What to add:**

1. **Run Configuration Comparison** (header section)
   - Judge model used for each run
   - Retrieval config comparison (top_k, diversity settings)
   - Corpus snapshot comparison (documents in common, added, removed)
   - Profile comparison (already partially done)

2. **Deterministic Check Comparison** (new metrics section)
   - Document presence pass rate: Model A vs Model B
   - Chunk alignment average: Model A vs Model B
   - Abstention accuracy: Model A vs Model B

3. **Per-Question Evidence Trail** (enhanced question breakdown)
   - Show required concepts with coverage status for each model
   - Show deterministic check results for each model
   - Color-code retrieval vs generation failures differently

4. **Enhanced Warning Display**
   - New warning types from Phase 3: JUDGE_MODEL_MISMATCH,
     RETRIEVAL_CONFIG_MISMATCH, CORPUS_CHANGED
   - More prominent display for warnings that affect comparison validity

## Exit Conditions

```bash
# Type check passes
cd packages/ui && pnpm type-check

# Lint and format pass
cd packages/ui && pnpm lint

# UI tests pass
cd packages/ui && pnpm test:run

# Dev server starts and pages render
cd packages/ui && pnpm dev
# Manual verification:
# - Evaluation detail page shows truth section for runs with truth data
# - Comparison page shows run metadata differences
# - Backward compat: old runs without truth/deterministic data render
#   without errors (sections simply not shown)
```

## What This Phase Does NOT Include

- Experiment history view (Phase 5)
- Cross-run trend visualization (Phase 5)
- Export/download of evaluation artifacts (future)

## Estimated PR Size

~500-600 lines of changed code (excluding tests). Split into two PRs:
- PR 4A: Truth and evidence display in evaluation detail (~300-350 lines)
- PR 4B: Enhanced comparison view + run metadata display (~250-300 lines)

## Review Gate

Before Phase 5 begins:
- Code review (code-reviewer agent) -- component quality, accessibility
- Test review -- UI component tests for new sections
- Manual testing -- verify rendering with truth data, without truth
  data, and with partial data
- Verify no regressions in existing evaluation and comparison views
