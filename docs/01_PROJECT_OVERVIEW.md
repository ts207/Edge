# Edge Project Overview

## What This Repository Is

Edge is a proposal-driven research platform for event-based crypto market discovery.

It exists to test claims like:

- "this event family appears under this context"
- "this template behaves differently under this regime"
- "this candidate survives costs, drift tolerances, and promotion gates"

It does not exist to maximize the number of backtests run or to turn detector output directly into trading claims.

## The Core Research Unit

The system is organized around a bounded hypothesis, not around a detector and not around an aggregated PnL chart.

A working research unit usually contains:

- event or trigger space
- template set
- context set
- symbol scope
- timeframe
- horizon set
- side / direction set
- entry lag set
- promotion profile
- search-control limits

Those inputs flow through proposal validation, planning, execution, evaluation, and promotion.

## End-to-End Operating Loop

The intended loop is:

`observe -> retrieve memory -> propose -> translate -> plan -> execute -> evaluate -> reflect -> adapt`

The operator guidance in `CLAUDE.md` is conservative by design:

- start narrow
- trust artifacts over impressions
- separate mechanical, statistical, and deployment conclusions
- leave a next action after each meaningful run

## Primary Entities

The most important repository entities are:

- proposal
  - compact YAML/JSON input for a bounded research question
- experiment config
  - repo-native config emitted from proposal translation
- run manifest
  - top-level execution and provenance record
- event definition
  - canonical event spec plus executable metadata
- state definition
  - context/state registry entry
- candidate
  - evaluated hypothesis row
- promotion decision
  - gated decision artifact with evidence
- strategy candidate / blueprint
  - post-promotion packaging surface

## Actual Pipeline Shape

The current implementation is broader than the old "8 box" diagram often repeated in stale docs.

The orchestrator composes stage families defined in `project/contracts/pipeline_registry.py`:

1. `ingest`
2. `core`
3. `runtime_invariants`
4. `phase1_analysis`
5. `phase2_event_registry`
6. `phase2_discovery`
7. `promotion`
8. `research_quality`
9. `strategy_packaging`

That distinction matters because runtime replay checks, event-registry canonicalization, and research-quality tails are now explicit execution surfaces.

## Source-of-Truth Surfaces

For repository intent:

- `docs/`
- `CLAUDE.md`

For live inventory:

- `docs/generated/`

For actual behavior:

- `project/pipelines/run_all.py`
- `project/contracts/pipeline_registry.py`
- `project/pipelines/pipeline_planning.py`
- `project/pipelines/pipeline_execution.py`

## Spec Layer vs Config Layer

The repo has two different declarative layers:

- `spec/`
  - static domain specs
  - events, ontology, grammar, objectives, runtime policy, search specs, templates, benchmarks
- `project/configs/`
  - runnable configuration
  - registries, workflow configs, live configs, synthetic configs, retail profiles

Confusing these two layers is a common source of stale documentation and incorrect changes.

## Generated Ontology and Routing

Current ontology work is not encoded only in prose. It is generated and audited.

Important generated outputs:

- `docs/generated/event_ontology_mapping.md`
- `docs/generated/canonical_to_raw_event_map.md`
- `docs/generated/context_tag_catalog.md`
- `docs/generated/composite_event_catalog.md`
- `docs/generated/strategy_construct_catalog.md`
- `docs/generated/event_ontology_audit.md`
- `docs/generated/regime_routing_audit.md`

Use these when you need the current ontology surface, not narrative claims copied into markdown months ago.

## What a Good Run Looks Like

A good run leaves:

- a bounded question
- a validated plan
- a clean manifest trail
- interpretable candidate / promotion artifacts
- a next action such as `explore`, `repair`, `hold`, or `stop`

Headline metrics alone do not qualify a run as good.

## What This Project Is Not

It is not:

- a generic backtesting playground
- a detector zoo that treats event materialization as strategy proof
- a synthetic-profitability showcase
- a notebook-first research stack
- a live execution system that ignores replay / artifact evidence
