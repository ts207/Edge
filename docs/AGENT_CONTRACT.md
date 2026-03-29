# Agent Operating Contract

## Allowed Actions

- Read and query only the repository-defined research surfaces before proposing work:
  - `project.domain.compiled_registry`
  - `project.research.regime_routing`
  - `project.research.agent_io.*`
  - `project.research.experiment_engine`
  - `project.research.phase2_search_engine`
  - `project.research.services.*`
  - `project.research.knowledge.query`
  - `project.research.search_intelligence`
- Create or update bounded proposal files, review files, scorecards, and run notes.
- Run `project.research.agent_io.proposal_to_experiment`, `project.research.agent_io.issue_proposal`, and `project.research.agent_io.execute_proposal`.
- Run one regime-scoped experiment at a time.
- Compare a new run only against a directly relevant prior run using `project/scripts/compare_research_runs.py`.
- Make local fixes only when they are narrow, contract-preserving, and directly necessary to recover the bounded loop.
- Add or tighten tests covering the exact surface touched by a local fix.

## Forbidden Actions

- Editing canonical ontology, routing, or contract surfaces without explicit human approval:
  - `spec/events/event_registry_unified.yaml`
  - `spec/events/regime_routing.yaml`
  - `project/contracts/pipeline_registry.py`
  - `project/contracts/schemas.py`
  - `project/engine/schema.py`
  - `project/research/experiment_engine_schema.py`
  - `project/strategy/dsl/schema.py`
  - `project/strategy/models/executable_strategy_spec.py`
- Adding new events, regimes, templates, detectors, or states as part of routine research.
- Relaxing promotion thresholds, cost assumptions, sample-quality floors, or multiplicity controls to rescue a weak hypothesis.
- Running broad searches across multiple unrelated regimes in one experiment.
- Conflating research evidence with executable-strategy truth or with live-readiness.
- Performing uncontrolled refactors, compatibility-layer rewrites, or large pipeline changes during routine research.

## Bounded Hypothesis Definition

A bounded hypothesis must state exactly:

- one canonical regime,
- one mechanism,
- one tradable expression,
- one primary trigger family,
- one template family,
- one symbol set,
- one timeframe,
- one start/end window,
- one horizon set,
- one direction set,
- one entry-lag set,
- one clear success test,
- one clear kill condition.

Invalid bounded hypothesis examples:

- "Find alpha in crypto."
- "Search all dislocations and all templates."
- "Use the model to predict returns regardless of regime."

## Valid Regime-Scoped Experiment Definition

A valid autonomous experiment is one that:

- scopes `trigger_space.canonical_regimes` to exactly one canonical regime,
- uses no more than one mechanism family per run,
- uses no more than one primary tradable expression per run,
- stays within proposal-settable knobs accepted by `project.research.agent_io.proposal_schema`,
- produces a validated plan through `project.research.experiment_engine`,
- writes canonical artifacts under the run-scoped paths used by `project.research.services.pathing`,
- ends with an explicit keep/modify/kill decision.

## Artifact Obligations For Every Run

Every autonomous run must produce and review:

- proposal copy, `experiment.yaml`, and `run_all_overrides.json` from `project.research.agent_io.issue_proposal`
- run manifest under `data/runs/<run_id>/run_manifest.json`
- `data/reports/phase2/<run_id>/phase2_candidates.parquet`
- `data/reports/phase2/<run_id>/phase2_diagnostics.json`
- promotion artifacts under `data/reports/promotions/<run_id>/`
- a human-readable experiment review using `experiment_review_template.md`
- an edge-registry row update using `edge_registry_template.md`

If promotion is intentionally disabled, the run is not valid for the default autonomous loop and must be marked exploratory-only.

## When Local Fixes Are Allowed

The agent may propose and implement a local fix only when all of the following are true:

- the fix is directly triggered by a bounded run, test failure, or artifact inconsistency,
- the fix preserves canonical schemas and existing meaning,
- the fix is local to boundary shaping, diagnostics, smoke fixtures, reporting, tests, or documentation,
- the fix includes targeted verification for the touched surface,
- the fix does not widen search scope or relax evidence standards.

Examples of allowed local fixes:

- repair missing lineage columns in a report writer,
- add a targeted regression test for proposal parsing or artifact metadata,
- fix a smoke fixture that drifted from canonical contracts,
- add review templates or verification automation.

## Escalate To Human Immediately When

- the required fix touches any forbidden contract surface listed above,
- the hypothesis requires a new ontology element, detector, or template,
- artifact layers disagree in a way that changes business meaning,
- verification still fails after one local bounded repair attempt,
- the result only works after threshold relaxation or cost-assumption weakening,
- the claim would require engine or execution-model reinterpretation,
- the agent cannot explain the mechanism in regime terms.

## Verification Obligations

After any code or config change, run the contract block defined in `researcher_verification.md`.

After any bounded experiment, run the experiment block defined in `researcher_verification.md`.

If verification fails:

- stop,
- record the failure,
- classify the issue as `repair` or `kill`,
- do not continue with additional experiments until the failure is resolved or escalated.

## Valid Edge Claim Standard

A valid edge claim must be phrased as:

"Within canonical regime `<regime>`, trigger family `<event/state>`, template `<template>`, symbol scope `<symbols>`, timeframe `<timeframe>`, and horizon `<horizon>`, the mechanism `<mechanism>` shows evidence of after-cost and stressed survivability under the repository’s research gates, with no contract or artifact contradictions."

A valid edge claim must never be phrased as:

- universal alpha,
- market prediction without regime conditioning,
- deployment readiness based only on discovery or backtest output,
- live-readiness without separate execution and canary evidence.

## Keep / Modify / Kill Standards

- `keep`
  - mechanism survives cost-aware review,
  - holdout and promotion evidence are not contradicted,
  - artifacts are complete and contract-valid,
  - next step is confirmatory, not broader discovery.
- `modify`
  - mechanism remains plausible but scope, context, expression, or implementation needs one bounded change,
  - next run stays in the same regime and narrows the question.
- `kill`
  - mechanism is contradicted,
  - cost-aware evidence fails cleanly,
  - negative controls or holdout support fail materially,
  - or the run exposed structural unreliability that invalidates the claim.
