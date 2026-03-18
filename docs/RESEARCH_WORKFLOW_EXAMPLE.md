# Research Workflow Example

## Purpose

This document shows one complete example of repo-native research work.

It is not a universal recipe and it is not a claim that the example setup is profitable.

Its purpose is to show:

- how an operator should think through a research question
- how to translate that question into repo-native terms
- what order of actions to take
- which artifacts to inspect
- how to interpret results correctly
- how to decide what to do next

The example below is intentionally narrow. It demonstrates good research discipline, not broad search.

## Example Scenario

We want to study whether a funding dislocation can support a short-horizon mean-reversion setup when volatility
is elevated but execution is still acceptable.

In repo-native terms, that means:

- event: `FND_DISLOC`
- family: `STATISTICAL_DISLOCATION`
- candidate template: `mean_reversion`
- candidate context: high `vol_regime`, acceptable `ms_spread_state`
- candidate horizon: short to medium intraday horizons

The question is not:

- "is funding dislocation alpha"

The question is:

- "does `FND_DISLOC + mean_reversion` survive costs on short horizons when volatility is high and spread stress is
  not hostile"

That is the correct level of specificity.

## Why This Example Is Good

This example is useful because it forces the operator to keep several boundaries clear:

- event versus family
- event versus template
- context versus post hoc story
- detector success versus research success
- discovery versus promotion

It is also a good example because it can fail in multiple meaningful ways:

- detector did not materialize the event correctly
- the idea only works in train and not in validation or test
- the setup is statistically plausible but not tradeable after costs
- the setup is mechanically fine but promotion rejects it

Each of those outcomes implies a different next action.

## Step 1: Start With An Observation

Suppose the operator sees one of the following:

- prior runs show `FND_DISLOC` candidates with promising raw expectancy but weak holdout support
- synthetic truth validation says funding dislocation recovery is working mechanically
- prior promotion results suggest rejection comes from sample quality or cost survival, not missing contracts

That is enough to justify a narrow follow-up.

The operator should write the initial thought like this:

- "Funding dislocation may support mean reversion, but only in high-volatility windows where the dislocation is
  real and the spread is still tradeable."

That statement already contains:

- the event
- the family intuition
- the template intuition
- the likely conditioning context
- the primary operational caveat

## Step 2: Retrieve The Right Prior Memory

Before running anything, retrieve memory for:

- the same event: `FND_DISLOC`
- the same family: `STATISTICAL_DISLOCATION`
- the same template class: `mean_reversion`
- similar volatility and spread states
- the same prior fail gate, if one exists

The operator is trying to avoid these mistakes:

- rerunning the same weak region with different wording
- forgetting that a prior failure was mechanical rather than statistical
- overreacting to one attractive metric in one prior slice

The right mental question is:

- "What already happened in this family-template-context region, and what ambiguity is still unresolved?"

If memory already says the region failed cleanly multiple times under similar conditions, the correct action may
be to stop before any new run happens.

## Step 3: Define The Objective

The objective should be explicit and falsifiable.

Good objective:

- test whether `FND_DISLOC + mean_reversion` on 15m to 60m horizons survives costs when `vol_regime` is high and
  `ms_spread_state` is not hostile

Bad objective:

- run more funding dislocation experiments

The good objective tells the system:

- what to test
- where to test it
- what conditions matter
- what would count as success or failure

## Step 4: Translate The Idea Into Repo-Native Terms

At this stage, the thought process should move from narrative language to repository language.

Example translation:

- trigger space: `FND_DISLOC`
- template set: `mean_reversion`
- contexts: high `vol_regime`, normal or acceptable `ms_spread_state`
- directions: likely contrarian to the displacement
- horizons: short intraday horizons
- entry lags: immediate and small delayed entry only
- symbols: keep narrow unless prior evidence justifies widening

This is where ontology matters.

The operator is not free to invent any template. `FND_DISLOC` belongs to `STATISTICAL_DISLOCATION`, so the
research should start with legal dislocation-style templates such as:

- `mean_reversion`
- `overshoot_repair`
- defensive variants if the main use is gating

Starting with `trend_continuation` here would be a semantic mismatch unless a very specific reason exists.

## Step 5: Choose The Smallest Useful Experiment

The smallest useful experiment is one that can falsify the claim without broad search.

For this example, a good first batch is:

1. primary slice
   - `FND_DISLOC + mean_reversion + high vol + acceptable spread`
2. comparison slice
   - `FND_DISLOC + mean_reversion` without the context filter
3. optional adjacent slice
   - `FND_DISLOC + overshoot_repair + high vol + acceptable spread`

This batch is good because it answers three useful questions:

- does the conditioned claim work at all
- does the context improve the claim
- is the chosen template actually better than the closest adjacent legal template

This batch is bad if it expands into:

- many symbols
- many unrelated templates
- many unrelated families
- many contexts added because they might help

## Step 6: Plan Before Executing

Before a material run, generate a plan first.

The point of `plan_only` is to verify:

- the intended stages will run
- the requested event and templates are actually in scope
- the run is not accidentally broad
- expensive downstream work is not being triggered unnecessarily

Typical conservative command flow:

```bash
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.knowledge.query static --event FND_DISLOC
```

Then translate the proposal:

```bash
.venv/bin/python -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/fnd_disloc_experiment.yaml \
  --overrides_path /tmp/fnd_disloc_overrides.json
```

Then inspect the plan:

```bash
.venv/bin/python -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id fnd_disloc_mr_example_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/fnd_disloc_mr_example_001 \
  --plan_only 1
```

The operator should inspect the plan before running for real.

Questions to ask:

- is `FND_DISLOC` actually the event in scope
- is the template set limited to what we intended
- are the symbols and dates narrow enough
- are any irrelevant stages or broad search branches being pulled in

## Step 7: Execute Conservatively

Once the plan is confirmed, run the narrow slice.

Execution order should usually be:

1. narrow path first
2. broader path only if the narrow path is mechanically clean
3. promotion-path verification only if discovery outputs justify it

If the operator changed code or contracts, the correct order is even stricter:

1. targeted replay for repair verification
2. narrow discovery slice
3. broader run only after artifacts reconcile

The key logic is:

- the goal is not to maximize total outputs
- the goal is to answer one question with the smallest trustworthy run

## Step 8: Inspect The Right Artifacts In The Right Order

After execution, inspect artifacts in this order:

1. top-level run manifest
2. stage manifests
3. stage logs
4. phase 2 discovery outputs
5. bridge or promotion artifacts, if they exist
6. memory and reflection outputs

This ordering matters.

A common failure is to jump straight to candidate metrics without checking whether the pipeline path itself was
clean.

For this example, the first checks are:

- did the run complete
- did the intended event path execute
- do manifests agree with logs
- were the right artifacts written

Only then should the operator inspect:

- split counts
- `q_value`
- post-cost expectancy
- stressed expectancy
- bridge tradability
- promotion eligibility

## Step 9: Interpret The Result At The Right Level

The example run can produce several distinct outcome classes.

### Outcome A: Detector Worked, Hypothesis Failed

Example:

- `FND_DISLOC` events materialize correctly
- candidates exist
- validation and test support are weak
- costs erase expectancy

Correct interpretation:

- the detector is working
- the event is real
- the tested family-template-context claim is weak

Incorrect interpretation:

- funding dislocation does not matter

The negative result belongs to the hypothesis, not automatically to the whole family.

### Outcome B: Conditioned Slice Improves The Unconditioned Slice

Example:

- unconditional `FND_DISLOC + mean_reversion` is weak
- conditioned `high vol + acceptable spread` version is cleaner
- validation and test counts remain usable

Correct interpretation:

- context is doing real explanatory work
- the next move is likely a narrow exploit or adjacent exploration

Incorrect interpretation:

- every high-vol dislocation is good

The result may justify a narrower follow-up, not a broad deployment claim.

### Outcome C: Statistical Promise, Operational Failure

Example:

- candidate metrics look good
- manifests are stale or malformed
- downstream export or promotion artifacts are inconsistent

Correct interpretation:

- this is a repair outcome
- the economics are not yet trustworthy because the path is not mechanically clean

Incorrect interpretation:

- promotion logic is too strict

The next action here is `repair`, not `exploit`.

### Outcome D: Discovery Success, Promotion Failure

Example:

- discovery outputs are attractive
- promotion rejects because of split counts, cost survival, or hard gating

Correct interpretation:

- the hypothesis is interesting but not yet promotion-ready
- the next step may be confirmatory narrowing or stopping

Incorrect interpretation:

- promotion is wrong because the signal looks intuitive

Promotion is supposed to be conservative.

## Step 10: Decide The Next Action Explicitly

Every run should end with exactly one next action.

For this example, the choices mean:

- `exploit`
  - the conditioned setup looks strong enough to justify a confirmatory follow-up
- `explore`
  - the family is promising, but the next move should test an adjacent template or context
- `repair`
  - artifacts or contracts blocked correct interpretation
- `hold`
  - the idea is plausible, but support is too thin for escalation
- `stop`
  - the evidence is clean and negative enough that the line should be closed

This is the most important discipline rule in the entire workflow:

- do not end a run with vague optimism

The run must close with a concrete action.

## Worked Example Of A Good Reflection

This is what a good post-run reflection for the example might look like.

### Objective

- test whether `FND_DISLOC + mean_reversion` survives costs on short intraday horizons when volatility is high
  and spread conditions remain acceptable

### Executed Slice

- BTC only
- narrow date range
- `FND_DISLOC`
- `mean_reversion`
- high `vol_regime`
- acceptable `ms_spread_state`
- immediate and small delayed entry

### What Passed

- event path materialized correctly
- artifacts and manifests reconciled
- conditioned slice outperformed unconditional slice on post-cost expectancy

### What Failed

- validation and test counts remained too thin for promotion

### Belief Update

- funding dislocation may support a context-sensitive mean-reversion mechanism, but the current slice is still too
  thin to justify promotion

### Next Action

- `explore`

Why:

- the family-template pairing is still plausible
- the next best move is to test the closest adjacent legal template or broaden the date range slightly without
  broadening the family

## Example Of A Bad Reflection

This is what not to write:

- "Funding dislocation looked pretty good. Need more experiments."

That fails because it does not say:

- which hypothesis was tested
- what actually changed
- what failed
- what the next action is

## Example Command Order For A Narrow Research Run

This is the conservative order an operator should usually follow.

1. inspect memory and static knowledge
2. write a compact proposal
3. translate proposal to repo-native config
4. inspect `plan_only`
5. execute the narrow run
6. inspect manifests and logs
7. inspect discovery outputs
8. inspect promotion or downstream artifacts only if justified
9. write reflection
10. store the next action in memory

That order exists to stop the operator from doing the expensive and noisy parts before the narrow and reliable
parts.

## Advanced Interpretation Rules

### Rule 1: Evaluate At The Hypothesis Level

Do not say:

- "`FND_DISLOC` works"

Say:

- "`FND_DISLOC + mean_reversion + high vol + acceptable spread` showed conditioned improvement but still lacks
  holdout depth"

### Rule 2: Separate Mechanism Evidence From Economic Evidence

A detector can recover the right event mechanically while the trade hypothesis still fails economically.

Those are different findings and should be stored separately.

### Rule 3: Separate Discovery From Promotion

A strong discovery result can still be an appropriate promotion rejection.

If promotion says no, the burden is on the evidence to improve, not on the gate to soften automatically.

### Rule 4: Use Ontology To Narrow, Not To Decorate

If a new context or state does not change selection or interpretation in a durable way, do not add it just to
make the story sound sharper.

### Rule 5: Respect Precedence

If spread stress or execution friction is hostile, do not let a lower-precedence family talk you into a trade.

## Common Mistakes In Example Workflows

- starting from a desired trade shape instead of a family-appropriate event
- using too many contexts at once
- skipping `plan_only`
- reading detector success as strategy success
- treating a synthetic positive as live-market evidence
- broadening symbols and dates before the narrow path is stable
- interpreting promotion failure as proof that the gate is too strict
- ending the run without a single explicit next action

## How To Expand From One Good Example

Once one narrow example is working, expansion should still be structured.

Safe expansion order:

1. same event, same template, slightly wider date range
2. same event, adjacent legal template
3. same family, adjacent event
4. same event-template pair, additional symbol
5. only then consider broader search

Unsafe expansion order:

1. many symbols
2. many templates
3. many unrelated families
4. promotion-path work before discovery is stable

## Recommendations

- keep one written experiment card per run
- store memory in family-template-context language
- prefer one narrow strong example over many vague searches
- use this workflow as a discipline template, not as a fixed alpha recipe
- teach new operators to explain what they are testing before they run anything

## Final Takeaway

A good research run is not the one with the highest headline number.

It is the run that leaves behind:

- a bounded question
- a semantically correct hypothesis
- a clean artifact trail
- a correct interpretation
- one justified next action

That is what this repository is designed to support.
