# Live thesis store and overlap

This document explains the runtime-facing packaged thesis model.

## Why the thesis store matters

The live/runtime layer should not reason from raw run notes, loose candidate rows, or human summaries.

It should reason from packaged thesis objects with explicit clauses and governance metadata.

That is why `data/live/theses/` exists.

Runtime should be pointed at one explicit thesis batch via `strategy_runtime.thesis_path` or `strategy_runtime.thesis_run_id`.
It should not rely on an implicit latest batch.

## Canonical thesis-store paths

Primary paths:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json` as a catalog artifact
- `data/live/theses/index.json -> runtime_registrations` for explicit named registrations when operators choose to record them

The batch file is the runtime contract. The index is metadata about available batches, not the preferred runtime selector.

## What a packaged thesis contains

A packaged thesis object typically carries:

- thesis id
- primary event id and event family
- canonical regime
- trigger clause
- confirmation clause
- context clause
- invalidation clause
- governance fields
- evidence summary
- promotion class
- deployment state
- overlap group id
- source lineage
- symbol scope and timeframe

This is the runtime contract. It is much richer than a simple research candidate row.

## Runtime ownership

Primary live/runtime modules include:

- `project/live/thesis_store.py`
- `project/live/retriever.py`
- `project/live/context_builder.py`
- `project/live/decision.py`
- `project/live/policy.py`
- `project/live/execution_attribution.py`
- `project/portfolio/thesis_overlap.py`
- `project/portfolio/risk_budget.py`

These modules assume packaged thesis objects exist and are structurally valid.

## Overlap graph

The overlap graph describes when packaged theses should not be treated as independent bets.

Current generated surfaces:

- `docs/generated/thesis_overlap_graph.json`
- `docs/generated/thesis_overlap_graph.md`

Overlap can be driven by shared structure such as:

- event families
- episode requirements
- canonical regime dependencies
- confirmation structure
- invalidation structure
- mechanism similarity

The point is not just reporting. The overlap graph informs downstream allocation and throttling logic.

## Deployment state and promotion class in runtime

Runtime should read both fields explicitly, but permission should be derived from deployment state first.

Examples:

- `monitor_only` means the thesis may be monitored but not traded
- `paper_only` means the thesis may be used in paper/shadow contexts but not traded
- `live_enabled` is the only deployment state that may reach trading runtime
- promotion class still carries evidence context such as `seed_promoted`, `paper_promoted`, or `production_promoted`

Any runtime shortcut that collapses these into one maturity flag is conceptually wrong.
Any runtime shortcut that resolves "whatever batch is latest" is also conceptually wrong.

## What to inspect after packaging changes

Use this order:

1. `data/live/theses/<run_id>/promoted_theses.json`
2. runtime config that references that batch explicitly
3. `docs/generated/thesis_overlap_graph.md`
4. any shadow-live summaries under `docs/generated/` or `data/reports/shadow_live/`
5. `docs/generated/seed_thesis_catalog.md` only for advanced bootstrap maintenance
6. `docs/generated/seed_thesis_packaging_summary.md` only for advanced bootstrap maintenance

## Current snapshot implication

Because the thesis store and overlap graph are already present, runtime docs should be written from the standpoint of an active packaged-thesis system.

The runtime layer is not waiting for a future packaging design. It already consumes a real packaged-thesis contract.
