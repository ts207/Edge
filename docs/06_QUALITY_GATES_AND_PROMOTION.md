# Quality gates and promotion

A run is trustworthy only when it survives more than one kind of check.

## Quality is multi-layered

Do not compress quality into one number.

A good result in this repo has to survive at least these layers:

1. **contract integrity** — proposal, schema, and artifact contracts are valid
2. **mechanical integrity** — required inputs and outputs exist and reconcile
3. **statistical quality** — the candidate survives phase-2 style filters
4. **promotion quality** — the candidate survives stronger promotion-oriented rules
5. **packaging quality** — the thesis object is packaged with evidence, governance, and runtime-safe fields
6. **deployment discipline** — promotion class and deployment state are not conflated

## Mechanical quality

Mechanical quality asks whether the run is even interpretable.

Typical blockers:

- missing manifest or missing required outputs
- broken schema or artifact contracts
- missing dataset coverage
- replay or runtime-invariant failures
- inconsistent generated artifacts

A run that fails mechanically is a repair problem, not a market-signal conclusion.

## Statistical quality

Phase-2 style quality asks whether a bounded claim has enough evidence to stay alive.

Typical dimensions include:

- sample count
- sign stability
- robustness
- cost-adjusted expectancy
- multiple-testing controls
- regime behavior

This is where candidates are kept, weakened, or rejected as research results.

## Promotion quality

Promotion asks a stricter question:

> Is the surviving candidate strong enough to be carried forward as a governed edge or packaged thesis input?

Promotion logic is owned by `project/research/services/promotion_service.py`.

Common promotion concerns include:

- q-value thresholds
- minimum event/sample support
- stability score
- sign consistency
- cost survival ratio
- negative-control behavior
- time-slice or regime-slice support
- overlap or redundancy concerns

## Promotion ladder

These lifecycle labels remain useful internally, but they are not the primary operator-facing permission model.

The lifecycle used by the repo is:

1. `candidate`
2. `tested`
3. `seed_promoted`
4. `paper_promoted`
5. `production_promoted`

This ladder is meaningful. Do not collapse it into a generic “good thesis” label, but also do not mistake it for runtime permission.

### `candidate`

The claim exists as a structured research output, but it is not yet packaged as a reusable thesis.

### `tested`

The claim has enough supporting testing structure to be tracked in the bootstrap lane.

### `seed_promoted`

The claim is packaged strongly enough for thesis-store membership and monitor-oriented use.

This is not the same thing as production readiness.

### `paper_promoted`

The claim clears a stronger bar for paper-style review or downstream non-live evaluation.

### `production_promoted`

This is the strongest class. It should be rare and deliberately earned.

## Promotion class versus deployment state

These are separate fields for a reason.

- **promotion class** = how strong the evidence is
- **deployment state** = where the thesis may be used now

For operator decisions, deployment state is the primary permission model:

- `monitor_only` means no trading
- `paper_only` means paper/shadow use only
- `live_enabled` is the only state that permits trading runtime

Typical pairings:

- `seed_promoted` + `monitor_only`
- `paper_promoted` + `paper_only`
- `production_promoted` + `live_enabled`

Never infer one from the other.

## Operator-facing readout

When summarizing whether something can be used by runtime, prefer this order:

1. was a thesis batch exported from a specific run
2. what deployment state that batch carries
3. what evidence caveat the promotion class still implies

That order is clearer than leading with `seed_promoted` / `paper_promoted` / `production_promoted`.
The question "can this trade?" should be answerable from deployment state alone.

## Bootstrap lane quality

The bootstrap lane adds another layer beyond candidate survival.

A packaging-ready thesis should have a coherent chain across:

- seed inventory membership
- testing scorecards
- empirical summaries
- evidence bundles
- packaging summary
- overlap graph membership
- thesis-store serialization

If one of those is missing, the thesis may still be interesting, but the packaging state is incomplete.

## Current packaging policy implication

In this snapshot, the thesis store already exists under `data/live/theses/`. That means promotion and packaging are active concepts in the repo rather than placeholders.

## How to classify a bad result

Use these buckets.

### Mechanical failure

The run or artifact path is broken.

Action: repair the pipeline, config, or artifact contract.

### Low-power failure

The strongest row exists but sample size is too small to treat the outcome as decisive.

Action: widen sample or coarsen the slice carefully.

### Regime-instability failure

The effect flips or collapses across regimes or time slices.

Action: freeze regime assumptions and run confirmatory follow-ups.

### No-effect failure

The bounded claim is simply not supported.

Action: kill or reframe.

## Common mistakes

- treating positive expectancy as enough
- ignoring multiple-testing and stability issues
- assuming a promoted row is a packaged thesis
- assuming `seed_promoted` means live-ready
- leading with promotion class when deployment state is the actual runtime permission
- reading only one table and inferring the entire quality story
