# Future Milestones

## Purpose

This document turns the current repository state into a practical forward roadmap.

It is not a product-marketing roadmap and it is not a promise that every item should be built immediately.

Its job is to answer:

- what the next major project milestones are
- why they matter
- what "done" should mean for each milestone
- what order makes sense given the current platform state

This roadmap assumes the current baseline:

- the repo has a cleaner package surface and stronger architecture boundaries
- the core research doc set exists
- the synthetic fast-certification path exists
- the maintained six-month synthetic truth baseline exists
- the detector ledger now distinguishes hard-gate truth targets, supporting signals, and live-only diagnostics

## How To Read This Roadmap

Use the milestones as sequencing guidance, not as a command to do everything at once.

A good milestone should:

- reduce uncertainty
- improve research quality
- improve operational reliability
- make future work cheaper

A bad milestone usually:

- adds breadth before the core path is trustworthy
- adds labels or features without changing decisions
- increases research surface faster than the team can evaluate it

## Milestone 1: Operationalize The Current Research Baseline

### Goal

Turn the current synthetic and narrow-run workflow into an expected, repeatable operating baseline.

### Why It Matters

The repo now has enough structure to support disciplined research, but the baseline still depends too much on
manual operator knowledge.

If this milestone is not completed:

- regressions will be detected late
- operators will use inconsistent run patterns
- doc quality will exceed operational consistency

### Scope

- make the fast synthetic certification path part of normal pre-merge or pre-release validation
- keep the six-month calibrated truth baseline maintained and reproducible
- standardize the "narrow first" research workflow for operators
- keep docs and CLI flows aligned

### Done Means

- one documented certification command is treated as the default smoke gate
- one documented full synthetic truth command is treated as the maintained detector baseline
- the workflow in [RESEARCH_WORKFLOW_EXAMPLE.md](./RESEARCH_WORKFLOW_EXAMPLE.md) is reproducible without ad hoc
  operator invention
- failures are classified quickly as mechanical, statistical, contract, or policy issues

### Recommended Deliverables

- a short CI or release-validation entrypoint for fast synthetic certification
- a maintained command recipe for the six-month truth baseline
- one operator checklist for narrow discovery runs

## Milestone 2: Build A Maintained Research Benchmark Matrix

### Goal

Move from isolated runs to a maintained benchmark set organized by family, template, context, and regime.

### Why It Matters

Right now the repo can support disciplined research, but comparison is still too dependent on local memory and
one-off examples.

The project needs a stable benchmark layer so the team can answer:

- which family-template combinations are worth repeated attention
- which contexts reliably help or hurt
- which regions are structurally weak and should be deprioritized

### Scope

- define benchmark slices for a small number of canonical families
- record expected artifacts and comparison rules
- compare like-for-like runs only
- store benchmark outcomes in ontology-native language

### Done Means

- each major family has at least one maintained benchmark slice
- results are summarized as family-template-context findings, not just raw detector names
- repeated reruns are no longer needed just to remember what happened last month

### Recommended Starting Families

- `STATISTICAL_DISLOCATION`
- `TREND_STRUCTURE`
- `VOLATILITY_TRANSITION`
- `POSITIONING_EXTREMES`
- `LIQUIDITY_DISLOCATION`

### Recommended Deliverables

- a benchmark registry doc or config surface
- one maintained benchmark report per selected family
- memory updates written at the family-template-context level

## Milestone 3: Expand Live Historical Data Coverage

### Goal

Shift more important research from synthetic-only evidence toward trustworthy historical evidence.

### Why It Matters

Synthetic work is useful for calibration, mechanism testing, and guardrails, but it is not the final research
surface.

The project still needs richer live historical coverage for:

- positioning-dependent detectors
- microstructure-sensitive research
- promotion credibility
- real execution-feasibility analysis

### Scope

- expand and validate historical futures data coverage
- improve supporting live-data fields such as funding, open interest, mark, liquidations, and microstructure
  proxies where available
- keep synthetic and historical workflows clearly separated in interpretation

### Done Means

- a narrow research run can be repeated on real historical data with clean artifacts
- live-data diagnostics are no longer blocked by missing columns for core workflows
- detector families that are weak under synthetic assumptions can be studied on real data without contract hacks

### Recommended Deliverables

- maintained historical data foundation runs for BTC first
- data-coverage validation reports for live research campaigns
- a clear operator distinction between synthetic calibration runs and historical research runs

## Milestone 4: Strengthen Promotion And Confirmatory Research

### Goal

Make the transition from discovery to confirmatory evaluation more explicit and reliable.

### Why It Matters

The repo already distinguishes discovery from promotion, but future value depends on making that boundary harder
to misuse.

This milestone should reduce two common problems:

- over-reading attractive discovery outputs
- under-specifying what a confirmatory follow-up should look like

### Scope

- define clearer confirmatory-run patterns
- tighten how promotion interprets discovery evidence
- make promotion outcomes easier to trace back to specific family-template-context claims

### Done Means

- promotion rejection reasons are clearly actionable
- confirmatory runs are first-class and documented, not improvised
- operators can tell whether a promising result needs broader data, tighter context, or a stop decision

### Recommended Deliverables

- a confirmatory research doc or protocol extension
- improved promotion audit summaries grouped by ontology-native units
- clearer stored memory for "discovery promising, promotion rejected" cases

## Milestone 5: Improve Research Memory And Campaign Management

### Goal

Turn memory from a useful side surface into a maintained campaign-management system.

### Why It Matters

The current memory framework is conceptually sound, but long-running campaigns will become noisy if memory is
not structured and pruned aggressively.

The project needs memory that can answer:

- what has already been tried
- what changed materially
- which failures are final versus superseded
- where the next research dollar should go

### Scope

- campaign-level memory summaries
- supersession and invalidation rules
- stronger negative-memory handling
- better retrieval by family-template-context-failure mode

### Done Means

- repeated weak regions are not revisited accidentally
- operator summaries can be produced from stored memory without re-reading raw logs
- stale findings are clearly marked as superseded by cleaner reruns or code changes

### Recommended Deliverables

- campaign memory rollups
- a "tested regions" summary grouped by ontology-native units
- stronger memory hygiene rules for invalidated findings

## Milestone 6: Build Better Operator And Review Surfaces

### Goal

Make it easier to inspect the right evidence quickly.

### Why It Matters

A good research platform should not require operators to reconstruct every run from raw directories and logs.

Even if the artifacts are all correct, research quality will still suffer if:

- the right comparison is hard to find
- failure modes are scattered across files
- promotion and discovery outputs are hard to connect

### Scope

- improve reporting summaries
- improve run-comparison ergonomics
- build views around family-template-context units
- keep artifact surfaces aligned with actual operator questions

### Done Means

- one run can be reviewed quickly without log archaeology
- one comparison can be interpreted without manually joining many artifacts
- family-level and campaign-level summaries are straightforward to produce

### Recommended Deliverables

- improved reporting-service outputs
- family-template-context summary tables
- operator-friendly comparison reports for baseline versus candidate runs

## Milestone 7: Expand Strategy Packaging Carefully

### Goal

Move from promising research outputs toward reproducible, reviewable strategy packaging without pretending that
every promoted edge is production-ready.

### Why It Matters

The platform already has research, recommendation, blueprint, and strategy-building surfaces. The next maturity
step is to make those surfaces dependable and selective.

### Scope

- ensure only well-supported edges flow into strategy packaging
- keep packaging logic tied to ontology-native evidence
- improve the trace from promoted edge to blueprint and candidate strategy

### Done Means

- packaged strategies can be traced back to the exact research claims that justified them
- weak or noisy edges do not contaminate the strategy-building surface
- operators can explain why a packaged strategy exists

### Recommended Deliverables

- stronger traceability from promotion artifacts into blueprints
- better strategy-package reporting
- explicit guardrails against packaging low-support discoveries

## Milestone 8: Deepen Synthetic Worlds Selectively

### Goal

Only expand synthetic regimes where that expansion changes real research decisions.

### Why It Matters

Synthetic complexity can grow faster than its usefulness.

The project should only deepen synthetic worlds when the result helps:

- detector falsification
- guardrail testing
- family-level mechanism research
- promotion-path verification

### Scope

- add richer regimes only where current synthetic worlds block meaningful evaluation
- keep live-only diagnostics clearly separated
- avoid using synthetic detail as a substitute for historical evidence

### Done Means

- each new synthetic regime has a clear research purpose
- truth windows and supporting signals are explicit
- new synthetic coverage closes a real decision gap

### Recommended Deliverables

- targeted new synthetic regimes for families that are currently under-tested
- explicit synthetic truth contracts for any new primary targets
- clear documentation of which detectors remain supporting-only or live-only

## Milestone 9: Lock In Architecture And Contract Discipline

### Goal

Preserve the cleanup work already completed so the repo does not drift back into broad, ambiguous surfaces.

### Why It Matters

Research quality degrades quickly when the codebase loses architectural clarity.

This project now has:

- clearer package boundaries
- explicit package roots
- smaller core services
- stronger wrapper policies

Those gains should become durable policy, not just one successful cleanup pass.

### Scope

- keep compatibility wrappers thin
- keep large modules from regrowing unchecked
- keep generated docs and contract surfaces current
- strengthen preferred-import enforcement over time

### Done Means

- architecture tests reflect the intended public and internal surfaces
- service and pipeline surfaces stay entrypoint-focused
- docs remain synchronized with real package and contract state

### Recommended Deliverables

- continued architectural integrity tests
- refreshed generated diagnostics after surface changes
- periodic doc maintenance tied to real structural changes

## Recommended Order

The current highest-value order is:

1. operationalize the baseline
2. build the benchmark matrix
3. expand live historical data coverage
4. strengthen promotion and confirmatory research
5. improve memory and campaign management
6. improve operator and review surfaces
7. expand strategy packaging carefully
8. deepen synthetic worlds selectively
9. keep architecture and contract discipline locked in throughout

This order favors:

- trust before breadth
- comparison before expansion
- historical evidence before ambitious synthetic elaboration
- durable process before large downstream packaging effort

## Stop Signals

Pause or de-scope a milestone when:

- the mechanical path is still unstable
- the milestone adds breadth without decision value
- the work is mostly creating labels or configs without changing operator choices
- the team is still relying on vague interpretation rather than artifact-backed evaluation

## Final Guidance

The next good phase of this project is not "more experiments."

It is:

- a smaller number of better-defined research programs
- stronger benchmark discipline
- more trustworthy historical evidence
- clearer promotion and strategy boundaries
- better memory and operator surfaces

That is how the repository becomes a dependable research platform instead of a large collection of interesting
runs.
