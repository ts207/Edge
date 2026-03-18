# Research Workflow Example

This document shows one full example of repo-native research work.

It is intentionally narrow. The point is to show good discipline, not broad search.

## Example Question

We want to study whether a funding dislocation supports a short-horizon mean-reversion setup when volatility is elevated but execution is still acceptable.

Repo-native translation:

- event: `FND_DISLOC`
- family: `STATISTICAL_DISLOCATION`
- template: `mean_reversion`
- context: elevated volatility, acceptable spread conditions
- horizons: short intraday

The question is not "is funding dislocation alpha."

The question is:

- does `FND_DISLOC + mean_reversion` survive costs on short horizons when context quality is favorable

## Step 1: Start With An Observation

Suppose prior runs suggest:

- detector truth is working mechanically
- raw expectancy sometimes looks promising
- holdout support or cost survival remains uncertain

That is enough to justify a narrow follow-up.

## Step 2: Retrieve Prior Memory

Before running anything, retrieve memory for:

- `FND_DISLOC`
- `STATISTICAL_DISLOCATION`
- `mean_reversion`
- similar volatility and spread contexts
- the same promotion or holdout fail gate, if one exists

The question here is:

- what ambiguity is still unresolved

If memory already shows repeated clean failure under the same conditions, stop.

## Step 3: Define The Objective

Good objective:

- test whether `FND_DISLOC + mean_reversion` on short intraday horizons survives costs when volatility is elevated and spread context is acceptable

Bad objective:

- run more funding dislocation experiments

## Step 4: Translate Into Repo Terms

Define:

- trigger space: `FND_DISLOC`
- template set: `mean_reversion`
- context family: volatility plus spread
- directions: contrarian to the displacement
- horizons: short intraday
- entry lags: immediate plus small delay
- symbols: narrow unless prior evidence justifies widening

## Step 5: Design The Smallest Useful Batch

A good first batch:

1. conditioned primary slice
   - `FND_DISLOC + mean_reversion + elevated vol + acceptable spread`
2. comparison slice
   - `FND_DISLOC + mean_reversion` without the context filter
3. optional adjacent slice
   - `FND_DISLOC + overshoot_repair + elevated vol + acceptable spread`

That batch answers:

- does the conditioned claim work
- does the context help
- is the nearest legal template better

## Step 6: Plan Before Executing

Inspect memory and static knowledge first:

```bash
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event FND_DISLOC
```

Translate the proposal:

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/fnd_disloc_experiment.yaml \
  --overrides_path /tmp/fnd_disloc_overrides.json
```

Inspect the plan:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id fnd_disloc_mr_example_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/fnd_disloc_mr_example_001 \
  --plan_only 1
```

Questions to ask:

- is `FND_DISLOC` really the trigger in scope
- are the templates limited to what was intended
- are the dates and symbols still narrow
- is confidence-aware context still enabled

## Step 7: Execute Conservatively

Execution order should usually be:

1. targeted replay if a repair must be verified
2. narrow discovery slice
3. broader path only after the narrow path is clean

The goal is to answer one question with the smallest trustworthy run.

## Step 8: Inspect Artifacts In Trust Order

Inspect in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. phase 2 outputs
5. bridge or promotion artifacts if they exist
6. memory and reflection outputs

If those disagree, stop broadening and repair first.

## Step 9: Interpret Results Correctly

Possible outcomes:

### Detector Works, Discovery Weak

Interpretation:

- the event materializes
- the market claim is not yet strong enough

Next action:

- `hold` or `explore` an adjacent context or template

### Discovery Looks Good, Promotion Rejects

Interpretation:

- the discovery claim is interesting
- confirmatory evidence or candidate quality is still insufficient

Next action:

- `exploit` through a confirmatory slice

### Run Fails Mechanically

Interpretation:

- no market conclusion should be drawn yet

Next action:

- `repair`

### Conditioned Slice Beats Unconditioned Slice

Interpretation:

- the context likely matters

Next action:

- validate the context claim on another comparable slice

## Step 10: Record Reflection

Capture:

- what belief was tested
- what changed
- what was market-driven versus system-driven
- what next action is justified

This is what turns one run into reusable memory instead of a one-off log trail.
