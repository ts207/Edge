# Artifacts and interpretation

This document answers a simple question: where do you look to understand what actually happened?

## Ask the right question first

Every artifact class answers a different question.

### What did we ask?

Proposal-memory artifacts:

- `data/artifacts/experiments/<program_id>/memory/proposals.parquet`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/proposal.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/experiment.yaml`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/run_all_overrides.json`

Use these when you need the exact normalized request and translation.

### What actually ran?

Primary run artifact:

- `data/runs/<run_id>/run_manifest.json`

The manifest is the mechanical source of truth. Read it before any summary or interpretation.

### What signal survived?

Research and promotion outputs:

- `data/reports/phase2/<run_id>/phase2_candidates.parquet`
- `data/reports/phase2/<run_id>/phase2_diagnostics.json`
- `data/reports/promotions/<run_id>/promotion_statistical_audit.parquet`
- `data/reports/promotions/<run_id>/promoted_candidates.parquet`
- `data/reports/promotions/<run_id>/promotion_decisions.parquet`
- `data/reports/promotions/<run_id>/promotion_summary.csv`
- `data/reports/operator/<run_id>/operator_summary.json`
- `data/reports/operator/<run_id>/operator_summary.md`

### What did runtime receive?

Runtime-facing thesis artifacts:

- `data/live/theses/<run_id>/promoted_theses.json`
- runtime config or invocation that points to that batch explicitly
- `data/live/theses/index.json`
- `docs/generated/thesis_overlap_graph.md`

## Canonical inspection order for a run

1. `data/runs/<run_id>/run_manifest.json`
2. `data/reports/phase2/<run_id>/phase2_candidates.parquet`
3. `data/reports/phase2/<run_id>/phase2_diagnostics.json`
4. `data/reports/promotions/<run_id>/...`
5. `data/reports/operator/<run_id>/operator_summary.*`

That order prevents a common mistake: interpreting research results before confirming the run was mechanically valid.

## What each artifact layer tells you

### Proposal memory

Use it to answer:

- which proposal version was issued
- how the proposal normalized
- what experiment bundle the operator path produced

### Run manifest

Use it to answer:

- what stages were planned and executed
- whether the run ended cleanly or mechanically failed
- what lineage and override state the run carried

### Phase-2 outputs

Use them to answer:

- whether there was any interesting effect at all
- which rows were strongest
- whether sample size and stability were credible

### Promotion outputs

Use them to answer:

- whether the strongest candidates survived stricter evidence gates
- which fail gate mattered most
- whether the result is interesting, exportable, or dead

### Thesis batch

Use it to answer:

- which run produced runtime-readable thesis objects
- which `deployment_state` values are present
- which packaged clauses and overlap metadata runtime will consume

## Canonical inspection order for packaged thesis state

1. `data/live/theses/<run_id>/promoted_theses.json`
2. runtime config or runtime invocation that references that batch explicitly
3. `docs/generated/thesis_overlap_graph.md`
4. `data/live/theses/index.json` as catalog metadata
5. bootstrap-maintenance summaries only if you are working in the advanced packaging lane

Do not start from `index.json` and infer what runtime selected. Start from the explicit runtime reference.

## Common interpretation errors

- reading markdown summaries before the manifest
- confusing a good candidate row with promotion survival
- confusing promotion survival with trading permission
- treating the existence of a packaged thesis as proof of `live_enabled`
- using generated summaries as if they were the primary evidence surface
