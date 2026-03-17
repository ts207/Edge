# Experiment Protocol

## Goal

Experiments convert a research question into a bounded, replayable, and comparable repository run.

## Experiment Unit

A single experiment should be describable as:

- symbol set
- time range
- trigger or event
- context or regime
- template
- direction set
- horizon set
- entry lag set
- objective

If an experiment cannot be summarized this way, it is too vague.

## Experiment Types

### Repair Experiment

Purpose:

- verify a code or contract fix
- ensure prior failure mode is gone

Success criteria:

- expected artifacts exist
- failure no longer reproduces
- no new contract breakage

### Narrow Discovery Experiment

Purpose:

- isolate a specific signal region
- compare conditioned vs unconditioned behavior

Success criteria:

- enough samples by split
- coherent metrics
- interpretable outcome

### Promotion-Path Experiment

Purpose:

- verify candidate propagation into export, promotion, and registry update

Success criteria:

- candidate fields survive the chain
- promotion rejects or accepts for substantive reasons


### Synthetic Validation Experiment

Purpose:

- verify detector recovery against known planted regimes
- verify promotion and guardrail behavior across controlled worlds

Success criteria:

- synthetic truth validation passes or expected misses are explained
- promotion outcomes are consistent with the planted mechanism and cost assumptions
- results survive at least one additional profile or seed when the hypothesis is strengthened

### Full Loop Experiment

Purpose:

- validate end-to-end stability when the local path is ready

Success criteria:

- all planned stages terminate cleanly
- manifests reconcile
- outputs are explainable

## Experiment Design Rules

- Change one important variable at a time when debugging.
- Keep symbol/time scope narrow during repair.
- Use explicit contexts for regime-conditioned claims.
- Avoid broad exploratory runs if prior runs already show the region is weak.
- Record why the experiment exists before running it.

## Batch Construction

Every batch should include:

- primary hypothesis
- reason for inclusion
- prior memory reference
- stop condition

Recommended sequence:

1. confirm the path works
2. test the strongest hypothesis
3. test one adjacent alternative

## Evaluation Checklist

For each candidate or experiment result, check:

- `train_n_obs`
- `validation_n_obs`
- `test_n_obs`
- `q_value`
- post-cost expectancy
- stressed post-cost expectancy
- regime stability
- bridge tradability
- promotion eligibility

## Reflection Template

For each completed experiment, write:

- objective
- actual executed slice
- key metrics
- anomalies
- belief update
- next action

## Stop Conditions

Stop a line of inquiry when:

- repeated runs fail for the same substantive statistical reason
- the region shows no post-cost viability
- support exists only in train and not in validation/test
- the implementation path is still mechanically unstable

## Promotion Discipline

Do not over-interpret discovery outputs.

A discovery is not a promoted edge.
A promoted edge is not a production strategy.
A full-loop agent must maintain those boundaries.

Synthetic experiments should record the generator profile and truth-map path in the reflection.
