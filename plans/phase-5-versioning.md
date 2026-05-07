# Phase 5: Versioning and Experiment Tracking (Future)

## Goal

Enable regression analysis and experiment comparison across time.
Track changes to truth sets, profiles, prompts, and retrieval strategies
so users can answer questions like:
- Did the new retrieval config improve completeness?
- Did prompt changes reduce hallucinations?
- How does Model X perform across different question sets?

## Status

**Deferred** -- This phase is documented for future planning but is not
scheduled for immediate implementation. Phases 1-4 must be complete and
stable before this work begins.

## Why Deferred

The QuickStart should focus on making individual evaluations excellent
before adding experiment management. Versioning adds schema complexity,
UI surface area, and maintenance burden that is not justified until the
core evaluation pipeline is mature and validated by users.

## Scope (When Undertaken)

### Basic Version Tracking

- Version truth sets (hash of content, sequential version number)
- Version profiles (already has `version` field, needs enforcement)
- Version prompts (system prompt hash stored on run)
- Record retrieval strategy version on each run

### Experiment History

- Group runs by experiment (same question set, different models/configs)
- Show trend charts: metric scores over time per model
- Show regression alerts: metric degradation from prior runs

### Cross-Run Model Comparison

- Compare a single model's performance across different question sets
- Compare a single model's performance across corpus changes
- Aggregate win/loss records across multiple comparisons

## Estimated Effort

2-3 PRs, ~800-1000 lines of changed code. Requires new DB tables
(experiment, experiment_run), API endpoints, and UI views.

## Prerequisites

- Phases 1-4 complete and stable
- User validation that the current evaluation pipeline meets needs
- Decision on whether experiment tracking justifies the complexity
  for a QuickStart (vs being a full product feature)
