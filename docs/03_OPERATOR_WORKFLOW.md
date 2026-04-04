# Operator workflow

This document owns the normal operator loop.

The canonical path is:

`proposal -> explain -> preflight -> plan -> run -> review -> export thesis batch`

## Step 1: author one bounded proposal

The operator front door is one atomic hypothesis, not an open search space.

Canonical example:

- [`spec/proposals/canonical_event_hypothesis.yaml`](/home/irene/Edge/spec/proposals/canonical_event_hypothesis.yaml)

Minimal shape:

```yaml
program_id: volshock_btc_long_12b
description: Long continuation after VOL_SHOCK on BTCUSDT 5m
start: "2024-01-01"
end: "2024-01-31"
symbols: [BTCUSDT]
timeframe: 5m
instrument_classes: [crypto]
hypothesis:
  trigger:
    type: event
    event_id: VOL_SHOCK
  template: continuation
  direction: long
  horizon_bars: 24
  entry_lag_bars: 1
```

The operator loader validates this shape strictly, then compiles it into legacy `AgentProposal` so downstream experiment code does not need to change.

## Step 2: explain the normalized proposal

Use explain before planning when you want to inspect what the repo believes you asked for.

```bash
edge operator explain --proposal <proposal.yaml>
```

`explain` is the fastest way to inspect:

- proposal format detection
- normalized `AgentProposal`
- compiled trigger space
- resolved experiment summary
- estimated hypothesis count

Use this to catch normalization mistakes before you look at pipeline behavior.

## Step 3: preflight

Use preflight to verify that the proposal is valid, translatable, and locally runnable.

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight
```

Direct CLI:

```bash
edge operator preflight --proposal <proposal.yaml>
```

Preflight checks:

- proposal loading and validation
- experiment translation viability
- search-spec availability
- local dataset coverage
- writable artifact root

Preflight does not create a durable run and does not change runtime state.

## Step 4: plan

Use plan to materialize the executable research contract without committing to full execution.

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=plan
```

Direct CLI:

```bash
edge operator plan --proposal <proposal.yaml>
```

Planning writes or reports:

- normalized proposal expansion
- `experiment.yaml`
- `run_all_overrides.json`
- required detectors, features, and states
- estimated hypothesis count
- proposal memory metadata

If the proposal includes `bounded:`, this is also where the baseline proposal is normalized and checked so the bounded diff happens on comparable `AgentProposal` objects.

## Step 5: run

Use run to create a durable research run with manifests and reports.

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=run
```

Direct CLI:

```bash
edge operator run --proposal <proposal.yaml>
```

Under the hood, the operator path:

1. loads and normalizes the proposal
2. validates bounded-mode constraints if present
3. writes proposal memory
4. writes `experiment.yaml`
5. writes `run_all_overrides.json`
6. invokes `project.pipelines.run_all`
7. updates run-scoped manifests and reports

## Step 6: inspect the run

Inspect outputs in this order:

1. `data/runs/<run_id>/run_manifest.json`
2. `data/reports/phase2/<run_id>/phase2_candidates.parquet`
3. `data/reports/phase2/<run_id>/phase2_diagnostics.json`
4. `data/reports/promotions/<run_id>/...`
5. `data/reports/operator/<run_id>/operator_summary.*`

The manifest answers whether the run is mechanically trustworthy. Promotion outputs answer whether the result survived the evidence gates strongly enough to matter.

## Step 7: review

There are three canonical post-run review surfaces.

Diagnose one run:

```bash
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose
edge operator diagnose --run_id <run_id>
```

Check regime sensitivity:

```bash
make review RUN_ID=<run_id> REVIEW_ACTION=regime-report
edge operator regime-report --run_id <run_id>
```

Compare a bounded follow-up against a baseline:

```bash
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
edge operator compare --run_ids <baseline_run,followup_run>
```

## Step 8: decide

Most runs end in one of these next actions:

- `repair` — the run or artifact contract broke
- `confirm` — the mechanism survives, but needs one bounded follow-up
- `kill` — the claim is not supported
- `export` — the run is good enough to become runtime-readable thesis input
- `package` — advanced/internal bootstrap maintenance, not the default path

## Step 9: export the thesis batch

Use export when one specific promoted run should become runtime input.

```bash
make export RUN_ID=<run_id>
```

Direct module form:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
```

This writes:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json` as catalog metadata

Optional explicit bridge controls live on the module surface:

```bash
python -m project.research.export_promoted_theses \
  --run_id <run_id> \
  --register-runtime <name> \
  --set-deployment-state <thesis_id_or_candidate_id>=monitor_only|paper_only|live_enabled
```

## Step 10: point runtime at the batch explicitly

Runtime should be configured with exactly one explicit thesis source:

- `strategy_runtime.thesis_path`
- or `strategy_runtime.thesis_run_id`

It should not infer “latest”.

Trading permission is still separate from export. Runtime may only trade when the selected thesis carries `deployment_state=live_enabled`.
