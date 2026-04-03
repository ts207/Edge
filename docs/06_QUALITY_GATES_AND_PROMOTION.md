# Quality gates and promotion

This repo does not treat one good backtest row as enough. Quality is layered.

## The six layers of trust

1. contract integrity
2. mechanical integrity
3. research/statistical quality
4. promotion quality
5. packaging quality
6. deployment discipline

A result is only trustworthy when it survives the layers relevant to the claim you are making.

## Layer 1: contract integrity

Questions:

- did the proposal validate
- did schemas reconcile
- did the plan build without violating repo contracts

Failure here means the question was not even asked cleanly.

## Layer 2: mechanical integrity

Questions:

- did the pipeline run as intended
- do required artifacts exist
- does the manifest reconcile with outputs
- did feature, data, or runtime-invariant checks fail

Failure here is a repair problem, not a market conclusion.

## Layer 3: research quality

Questions:

- is there any effect worth caring about
- does it survive costs and sample-quality checks
- does it remain directionally coherent across relevant slices

This is where a candidate becomes worth discussing.

## Layer 4: promotion quality

Promotion asks a narrower question:

> is the surviving candidate strong enough to carry forward as a governed thesis input?

Typical promotion concerns:

- q-value controls
- support and coverage
- stability
- sign consistency
- cost survival
- negative-control behavior
- time-slice or regime-slice support

## Layer 5: packaging quality

Packaging quality asks whether the result has been turned into a usable runtime contract with:

- explicit trigger and context clauses
- invalidation logic
- governance metadata
- evidence summaries
- overlap metadata
- serializable thesis-batch output

## Layer 6: deployment discipline

This is where many users get confused.

Evidence strength and runtime permission are separate.

- `promotion_class` answers how strong the evidence is
- `deployment_state` answers where the thesis may be used

Operator-facing permission should be read from deployment state:

- `monitor_only`
- `paper_only`
- `live_enabled`

`live_enabled` is the only state that may reach trading runtime.

## Internal promotion ladder

The repo still tracks:

1. `candidate`
2. `tested`
3. `seed_promoted`
4. `paper_promoted`
5. `production_promoted`

This ladder remains useful as internal evidence metadata. It is not the main operator-facing permission model.

## The operator-facing readout

When someone asks “can this trade?”, answer in this order:

1. was a thesis batch exported from a specific run
2. what `deployment_state` does that thesis carry
3. what evidence caveats still matter from `promotion_class`

That sequence is operationally clearer than starting from internal promotion vocabulary.

## Decision rubric after a run

### Repair

Use when artifact, schema, or manifest integrity failed.

### Confirm

Use when the mechanism still looks plausible but requires one bounded follow-up.

### Kill

Use when the claim is not supported after costs, stability, or regime review.

### Export

Use when the run produced promoted results strong enough to become runtime-readable thesis input.

### Package

Use only when you intentionally need broader bootstrap/governance maintenance beyond the one-run export path.
