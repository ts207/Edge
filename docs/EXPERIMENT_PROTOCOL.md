# Experiment Protocol

This document defines how to turn one research question into one bounded, replayable experiment.

## Purpose

An experiment should answer a specific question with the smallest trustworthy run.

It should not exist to generate lots of output.

## What An Experiment Is

A good experiment specifies:

- the belief being tested
- the repo-native trigger or event family
- the allowed template family
- the conditioning context
- the symbol and date scope
- the horizon and entry logic
- the pass and fail interpretation

## What A Good Experiment Looks Like

Good:

- one narrow objective
- one explicit ambiguity being resolved
- one attributable region of the search space

Bad:

- many unrelated families in one run
- many symbols without a reason
- many templates "just in case"
- expansion before the narrow path reconciles

## Experiment Card

Each material experiment should be describable in this shape:

- `objective`
- `run_scope`
- `trigger_space`
- `templates`
- `contexts`
- `directions`
- `horizons_bars`
- `entry_lags`
- `expected_artifacts`
- `success_condition`
- `failure_condition`

## Batch Design

Default batch composition:

- one primary slice
- one comparison slice
- optionally one adjacent slice

The comparison slice should answer one useful question such as:

- does context help
- is the adjacent legal template better
- is the effect robust to one small design variation

Do not add unrelated objectives into the same batch.

## Scope Rules

Keep scope narrow by default:

- one family before many
- one template family before many
- one context family before many
- one symbol before many unless cross-sectional behavior is the actual question

Widen only after the narrow slice is mechanically clean and statistically interpretable.

## Planning Rule

Use `plan_only` before material runs.

Planning should verify:

- the run is actually narrow
- the event set is correct
- the template set is correct
- the stages in scope are what you intended

If the plan looks broader than the objective, stop and fix the proposal.

## Execution Order

Default order:

1. repair replay if a code or contract change must be verified
2. narrow discovery slice
3. broader expansion only after reconciliation
4. confirmatory or promotion path only after discovery justifies it

## Evaluation Checklist

Every experiment should be evaluated for:

- artifact completeness
- manifest and log agreement
- split counts
- post-cost quality
- stressed quality
- context plausibility
- promotion relevance

## Stop Rules

Stop broadening an experiment when:

- the path is mechanically broken
- the idea fails cleanly on holdout
- the context claim adds no value
- promotion rejection is clearly explained and no new condition exists
- the next run would only restate the same failed question

## Promotion Discipline

Discovery and promotion are different surfaces.

A discovery result is not promotion-ready just because it looks attractive.

Promotion should only be trusted when:

- the candidate contract is valid
- split support exists
- costs and stressed quality survive
- the claim is narrow enough to understand

## Synthetic Discipline

When the experiment uses synthetic data:

- truth validation comes before interpretation
- short windows should be read as calibration unless holdout evidence exists
- cross-profile survival matters more than one strong synthetic world
