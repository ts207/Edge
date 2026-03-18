# Autonomous Research Loop

This document defines the default research loop for the repository.

Use it when deciding what to do next, how much to run, and when to stop.

## Purpose

The repo is designed to convert one observation into one or more bounded research actions, then convert the result into durable memory.

The loop is:

`observe -> retrieve memory -> define objective -> propose -> plan -> execute -> evaluate -> reflect -> adapt`

## Loop Outputs

A complete loop leaves behind:

- a bounded objective
- a run or replay artifact set
- an evaluation
- a reflection
- an explicit next action

If any of those are missing, the loop is incomplete.

## Phase 1: Observe

Collect the smallest evidence set that explains the current state:

- latest run manifests
- relevant stage manifests
- stage logs when needed
- discovery and promotion summaries
- quality and audit reports
- generated diagnostics when ownership or registry questions matter

Key questions:

- what was tried
- what failed mechanically
- what looked statistically interesting
- what is still ambiguous

## Phase 2: Retrieve Memory

Before proposing a new run, retrieve prior memory for:

- the same event or family
- the same template
- the same symbol or timeframe
- the same context
- the same fail gate

Do not rerun a region by default if memory already shows repeated clean failure with no material new condition.

## Phase 3: Define Objective

The objective must be explicit and falsifiable.

Good examples:

- test whether a basis dislocation continuation survives costs in low-liquidity windows
- verify whether a promotion rejection came from missing holdout support rather than weak economics
- isolate whether high-confidence trend context improves a specific template

Bad examples:

- find alpha
- try more experiments
- search more broadly

## Phase 4: Propose

Translate the objective into repo-native terms:

- trigger or event family
- template set
- context family
- directions
- horizons
- entry lags
- date and symbol scope

Use the ontology-native surfaces. Do not invent free-form categories when the registry already has a canonical form.

## Phase 5: Plan

Use `plan_only` before material runs.

Planning exists to verify:

- the requested stages are in scope
- the event and template set are actually what you intended
- the run is still narrow
- unnecessary downstream work is not being pulled in

If the plan is broader than the objective, fix the proposal before running.

## Phase 6: Execute

Default execution order:

1. targeted replay if code or contract changes must be verified
2. narrow discovery slice
3. broader expansion only after the narrow path reconciles

The repository should answer one question per run whenever possible.

## Phase 7: Evaluate

Evaluate on three layers:

### Mechanical

- stage completion
- artifact presence
- manifest and log agreement
- warning surface

### Statistical

- split counts
- multiplicity-aware quality
- post-cost expectancy
- robustness across splits or conditions

### Deployment Relevance

- friction feasibility
- promotion eligibility
- context stability
- plausibility of live execution

## Phase 8: Reflect

After every meaningful run, answer:

1. what belief was tested
2. what evidence changed that belief
3. what was market-driven versus system-driven
4. what reusable rule should be remembered
5. what exact next action is justified

## Phase 9: Adapt

Choose one next action:

- `exploit`: narrow positive evidence deserves a confirmatory or adjacent strengthening run
- `explore`: the result was informative, but the next move should test a nearby region
- `repair`: system or contract issues dominate and must be fixed first
- `hold`: evidence is too weak or ambiguous to justify more work now
- `stop`: the idea or path is not worth continuing under current evidence

## Escalation Rules

Escalate from narrow to broad only when:

- the narrow path is mechanically clean
- the target claim is still coherent
- there is enough support to justify more scope

De-escalate to repair mode when:

- manifests and logs disagree
- required artifacts are missing
- candidate contracts are malformed
- warnings obscure real failures

## Synthetic Branch

When the dataset is synthetic, the loop changes slightly:

1. freeze the profile before evaluating outcomes
2. keep the manifest and truth map with the run
3. validate truth before interpreting misses
4. compare across at least one additional profile before strengthening belief
5. separate detector recovery from profitability claims

## Definition Of Done

The loop is done only when:

- the artifacts reconcile
- the result is interpreted at the correct layer
- the next action is explicit
- memory has enough information to stop repeated rediscovery later
