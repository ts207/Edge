# Live thesis store and overlap

This document owns the runtime-facing thesis-batch model.

## The runtime contract

Runtime should consume packaged thesis objects from one explicit batch:

- `strategy_runtime.thesis_path`
- or `strategy_runtime.thesis_run_id`

It should not infer “latest”.

The canonical batch path is:

- `data/live/theses/<run_id>/promoted_theses.json`

## What the thesis store is for

The live layer should reason from governed thesis objects, not from:

- raw candidate rows
- markdown summaries
- ad hoc operator notes

That is why `data/live/theses/` exists.

## Canonical thesis-store paths

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json`
- `data/live/theses/index.json -> runtime_registrations` when operators record explicit named registrations

`promoted_theses.json` is the runtime payload.

`index.json` is catalog metadata. It is not the preferred runtime selector.

## What a packaged thesis contains

A packaged thesis typically includes:

- thesis id
- source run lineage
- symbol scope and timeframe
- trigger clause
- confirmation clause
- context clause
- invalidation clause
- evidence summary
- promotion class
- deployment state
- overlap metadata

This is much richer than a candidate row because runtime needs governance and invalidation structure, not only research statistics.

## Runtime permission model

Runtime should inspect both evidence and permission fields, but permission comes first from `deployment_state`:

- `monitor_only`
- `paper_only`
- `live_enabled`

`live_enabled` is the only state that may reach trading runtime.

`promotion_class` remains useful evidence context, but it should not be used as the main permission field.

## Overlap graph

The overlap graph answers which theses should not be treated as independent bets.

Generated surfaces:

- `docs/generated/thesis_overlap_graph.json`
- `docs/generated/thesis_overlap_graph.md`

Downstream portfolio and throttling logic use this structure to reason about concentration and shared mechanism risk.

## What to inspect after thesis changes

1. `data/live/theses/<run_id>/promoted_theses.json`
2. runtime config or invocation that references the batch explicitly
3. `docs/generated/thesis_overlap_graph.md`
4. `data/live/theses/index.json`
5. bootstrap-maintenance summaries only if you are working in the advanced package lane

## Conceptual errors to avoid

- collapsing promotion class and deployment state into one maturity flag
- treating the thesis index as if it were the runtime selector
- assuming an exported batch is automatically live tradable
- reasoning from overlap summaries without checking the actual thesis payloads
