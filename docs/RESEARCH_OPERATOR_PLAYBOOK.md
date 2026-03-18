# Research Operator Playbook

This document is the practical onboarding guide for a new repo operator.

Read this after [Root Operator Guide](../CLAUDE.md). It explains how to enter the system, what to trust, and how to avoid common misuse.

## What This Repo Is

This repo is a research operating system for market studies.

It is designed to:

- turn observations into explicit hypotheses
- run bounded experiments
- evaluate outputs against contract, statistical, and deployment gates
- store reusable memory
- support promotion only after evidence survives the required gates

It is not:

- a general-purpose strategy toybox
- a place to run broad searches because "more output is better"
- a system where detector firings alone count as evidence

## First Principles

Keep these rules in mind at all times:

1. artifacts are the source of truth
2. a run is only as trustworthy as its contracts
3. synthetic evidence is calibration evidence unless stated otherwise
4. confidence-aware context is the default for production research
5. promotion is a gate, not a reward for attractive discovery output

## The Operator Loop

The standard operating loop is:

1. observe
2. retrieve memory
3. define objective
4. translate into repo-native terms
5. inspect the plan
6. execute the smallest useful run
7. evaluate artifacts
8. write reflection
9. choose the next action

The next action should be one of:

- `exploit`
- `explore`
- `repair`
- `hold`
- `stop`

If the run does not end in one of those decisions, it is incomplete.

## The Repo-Native Research Unit

The correct unit of research is a hypothesis, not a detector and not a strategy.

A hypothesis combines:

- event
- canonical family
- template
- context
- side
- horizon
- entry lag
- symbol scope

That is the unit you should compare across runs, store in memory, and interpret in promotion.

## How To Start A New Question

Start by writing the question in plain language, then immediately convert it into repo-native language.

Example:

- plain language: funding dislocation may revert quickly in high volatility if spreads are still acceptable
- repo-native:
  - event: `FND_DISLOC`
  - family: `STATISTICAL_DISLOCATION`
  - template: `mean_reversion`
  - context: high volatility, non-hostile spread state
  - horizons: short intraday

If you cannot do that translation, the question is not ready to run.

## The Minimum Safe Run Pattern

Default to this sequence:

1. inspect memory
2. inspect static event knowledge
3. build a compact proposal
4. run `plan_only`
5. inspect the plan
6. execute the narrow slice
7. inspect artifacts in trust order

Do not skip `plan_only` for material runs.

## Trust Order

When reviewing a run, read evidence in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. report artifacts
5. generated diagnostics

If those disagree, the disagreement is a finding.

## What To Look For In Evaluation

Every meaningful run should be checked on three layers.

### Mechanical

- did the intended stages run
- do manifests and outputs reconcile
- are required artifacts present
- are warnings hiding runtime faults

### Statistical

- are there non-zero validation and test counts
- do metrics survive multiplicity and costs
- are results stable across splits

### Deployment Relevance

- is the idea still tradeable after friction
- is the result narrow and attributable
- is the idea context-stable enough to matter

## Confidence-Aware Context

Production research should treat context labels as quality-filtered, not absolute truth.

That means:

- hard state labels still exist
- context confidence and entropy are part of the normal evaluation surface
- ambiguous regime rows should usually be filtered out instead of treated as normal context hits

Use hard-label mode only as a baseline comparison or compatibility path.

## Maintained Benchmark Status

Use the maintained benchmark set deliberately. Do not assume every benchmark in the repo is equally authoritative.

Current operator default:

- start with the latest verified benchmark review artifact:
  - [/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_review.json](/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_review.json)
- use `VOL_SHOCK` as the maintained non-empty live context-comparison slice
- use `ZSCORE_STRETCH` as the maintained live statistical-dislocation comparison slice
- use `FALSE_BREAKOUT` quality-boundary mode when you need to see confidence-aware context demote a benchmark decision rather than merely reduce `n`
- use synthetic `BASIS_DISLOC` as the maintained synthetic statistical-dislocation authority
- do not treat live `FND_DISLOC` as a current maintained benchmark; it has been superseded by the `ZSCORE_STRETCH` live slice

The detailed status table lives in [Benchmark Status](./BENCHMARK_STATUS.md).

## Synthetic Versus Historical Research

Synthetic work answers:

- does the detector recover planted truth
- does the pipeline produce the expected artifacts
- does the search and promotion path behave as expected under controlled conditions

Historical work answers:

- does the setup survive on real market data
- are costs, slippage, and holdout support still acceptable
- is the signal still credible outside the simulator

Do not present synthetic profitability as live-market evidence.

## Common Operator Mistakes

Avoid these patterns:

- using many unrelated triggers in one run
- widening a run before the narrow version is reconciled
- reading detector truth as strategy truth
- reading discovery output as promotion readiness
- ignoring memory because the wording changed slightly
- trusting output count instead of trust quality

## What To Do After A Run

Always leave behind:

- a short statement of what was tested
- what passed
- what failed
- what is suspicious
- the exact next recommended action

If the result is mainly system-driven, say so directly.

If the result is mainly market-driven, say so directly.

Do not blur those two cases.

## The Core Docs After This One

Use these next:

1. [Autonomous Research Loop](./AUTONOMOUS_RESEARCH_LOOP.md)
2. [Experiment Protocol](./EXPERIMENT_PROTOCOL.md)
3. [Artifacts And Contracts](./ARTIFACTS_AND_CONTRACTS.md)
4. [Operations And Guardrails](./OPERATIONS_AND_GUARDRAILS.md)
5. [Research Workflow Example](./RESEARCH_WORKFLOW_EXAMPLE.md)
