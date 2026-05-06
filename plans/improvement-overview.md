# Evaluation Pipeline Improvement Plan

## Goal

Improve the QuickStart so it evaluates the whole RAG pipeline in a structured,
reproducible, and trustworthy way. Each evaluation run should clearly capture
what was asked, what the system considers true, what evidence was retrieved,
what each model answered, how each answer was scored, and why one passed or
failed.

## Guiding Principle

> Generate truth dynamically, but freeze it before evaluation.

## Key Design Decisions

1. **Database-first, not file-based artifacts.** The codebase uses PostgreSQL
   with `EvalRun`, `EvalResult`, and `QuestionSet` models. All new data
   (structured truth, deterministic check results, run metadata) goes into
   existing or new DB columns -- not parallel JSON files. One source of truth.

2. **Truth splits into answer_truth and retrieval_truth.** These are two
   different concerns: "what should the answer contain" vs "what evidence
   should be retrieved." Separating them at the schema level means
   downstream code reads from the right section without ambiguity --
   coverage.py reads answer_truth, deterministic checks read retrieval_truth.

3. **All questions with expected answers get full truth.** Manual questions
   are not treated as "partial truth." The corpus is always present before
   evaluation, so manual questions get retrieval truth by grounding the
   expected answer against the uploaded corpus using the same retrieval
   pipeline as evaluation. The only difference from synthesis is how
   retrieval truth is produced (`evidence_mode`), not whether it exists.

4. **Corpus grounding uses the evaluation retrieval path.** Manual question
   truth generation calls `retrieve_chunks()` from `retrieval.py` with the
   same profile-driven parameters. This ensures retrieval truth reflects
   what the evaluation pipeline would actually retrieve, not a different
   search method.

5. **Keep A/B comparison model.** Multi-model per run (N models evaluated in
   a single run) is architecturally sound long-term but would require
   reworking the entire DB schema, pipeline, comparison logic, and UI.
   Not justified at this maturity level. The current A/B approach stays.

6. **Deterministic checks absorb profile contract enforcement.** Vague rules
   like "do not invent thresholds" cannot be made reliably deterministic.
   The clearest profile rules (document presence, chunk alignment, abstention
   behavior, unsupported source references) become deterministic checks.
   Nuanced judgment stays with the existing GEval metrics.

7. **Synthesis improvement moves earlier.** The current synthesizer
   (`synthesizer.py`) selects chunks ordered by `Chunk.id` and limited to
   the first 50, heavily biasing toward the first ingested document. Biased
   synthesis poisons everything downstream, so this fix belongs in Phase 3,
   not deferred.

8. **Versioning and experiment tracking deferred.** Basic version fields
   (truth_schema_version, concept_extraction_version,
   evidence_alignment_version) are seeded in truth metadata now. Full
   experiment tracking is Phase 5 future work.

9. **Chunk IDs over filename:page references.** Use `chunk:{id}` as the
   canonical stored reference for expected chunks. Filenames can change on
   re-upload and page numbers depend on parsing. Display labels are derived
   from chunk records.

10. **Comparison storage is already correct.** The current architecture stores
    per-model results in the DB and computes comparison on demand. No changes
    needed to this pattern.

## Phase Summary

| Phase | Focus | PRs | Dependencies |
|-------|-------|-----|--------------|
| 1 | Structured Truth Foundation | 1-2 | None |
| 2 | Deterministic Evaluation Layer | 2 | Phase 1 |
| 3 | Run Fidelity and Synthesis Quality | 2 | Phase 1 |
| 4 | UI Explainability | 2 | Phases 2-3 |
| 5 | Versioning and Experiment Tracking | 1-2 | Phases 1-4 (future) |

Phases 2 and 3 can proceed in parallel after Phase 1 review.

Between each phase: comprehensive codebase review (code-reviewer +
security-engineer agents), test review, and PR.

See individual phase documents for details:
- [Phase 1: Structured Truth](phase-1-structured-truth.md)
- [Phase 2: Deterministic Evaluation](phase-2-deterministic-evaluation.md)
- [Phase 3: Run Fidelity and Synthesis](phase-3-run-fidelity-synthesis.md)
- [Phase 4: UI Explainability](phase-4-ui-explainability.md)
- [Phase 5: Versioning](phase-5-versioning.md)

## Phase Flow

```
Phase 1 (Truth) -> Review -> Phase 2 (Deterministic) -> Review -\
                          \-> Phase 3 (Fidelity)      -> Review --> Phase 4 (UI) -> Review
```

## What Already Exists (no work needed)

These capabilities from the original improvement plan are already
implemented in the codebase:

- **Pass/fail gates** -- `verdicts.py` implements critical thresholds,
  disqualification gates, and PASS/FAIL/REVIEW_REQUIRED verdicts
- **Coverage checking** -- `coverage.py` extracts concepts from expected
  answers, checks coverage against actual answers, and classifies missing
  concepts as retrieval vs generation failures
- **Comparison storage** -- Runs are stored in DB, comparisons computed
  on demand from stored per-model results
- **Profile-driven thresholds** -- YAML profiles define regular and
  critical thresholds, retrieval config, and system prompts

## What Is Explicitly Out of Scope

- Multi-model per run (N-way comparison in a single run)
- File-based artifact storage (run.json, truth.json, etc.)
- Full experiment tracking UI (trend charts, regression alerts)
- Embedding-based concept matching (keyword heuristic is sufficient)
- ArenaGEval head-to-head comparison (complementary but separate feature)
