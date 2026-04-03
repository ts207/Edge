# Operator workflow

This document explains the canonical bounded-work loop.

## Workflow summary

The operator path is designed to answer one bounded question at a time while leaving a complete artifact trail.

Canonical loop:

`proposal -> preflight -> plan -> run -> inspect manifest -> inspect candidates -> inspect promotion outputs -> diagnose/compare -> decide keep/modify/kill -> export thesis batch`

## Step 1 — author a bounded proposal

A proposal should be narrow enough that you can answer all of these before running it:

- what event or regime class is being tested
- what single template is being tested
- what single symbol is being tested
- what date window is allowed
- what contexts are included or excluded
- what exact horizon, direction, and entry lag are being tested
- whether this is research-only, confirmation-oriented, or bounded off a baseline run

A minimal example now exists at:

- `spec/proposals/canonical_event_hypothesis.yaml`

Operator-facing proposals now use a single-hypothesis shape:

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
  horizon_bars: 12
  entry_lag_bars: 1
```

The operator loader compiles this bounded front-door format into the legacy internal `AgentProposal`.

## Step 2 — preflight

Use preflight to verify that the proposal is structurally valid, local datasets resolve, and the artifact root is writable.

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight
```

Direct CLI:

```bash
edge operator preflight --proposal <proposal.yaml>
```

Preflight checks include:

- proposal validity
- validated plan generation
- search-spec existence
- local dataset coverage by symbol
- artifact-root writability

Use preflight before plan or run when the data root or proposal shape is uncertain.

## Step 3 — plan

Use plan to translate the proposal into a validated experiment config and a set of `run_all` overrides without committing to full execution semantics.

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=plan
```

Direct CLI:

```bash
edge operator plan --proposal <proposal.yaml>
```

What plan gives you:

- validated proposal expansion
- detector/feature/state requirements
- estimated hypothesis count
- experiment config bundle
- run-all override bundle
- a stable record under proposal memory

## Step 4 — run

Use run when the proposal is ready to become a durable run with artifacts.

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=run
```

Direct CLI:

```bash
edge operator run --proposal <proposal.yaml>
```

Under the hood, the operator path:

1. copies the proposal into proposal memory
2. writes `experiment.yaml`
3. writes `run_all_overrides.json`
4. invokes `project.pipelines.run_all`
5. updates proposal memory and run-scoped artifacts

## What gets written during proposal issuance

A normal operator-issued run produces three different classes of outputs.

### Proposal memory

Under:

- `data/artifacts/experiments/<program_id>/memory/`
- `data/artifacts/experiments/<program_id>/memory/proposals.parquet`
- `data/artifacts/experiments/<program_id>/memory/proposals/<run_id>/...`

### Run-scoped execution outputs

Typically under:

- `data/runs/<run_id>/run_manifest.json`
- `data/reports/phase2/<run_id>/...`
- `data/reports/promotions/<run_id>/...`

### Operator review outputs

Under:

- `data/reports/operator/<run_id>/operator_summary.json`
- `data/reports/operator/<run_id>/operator_summary.md`

## Step 5 — review the run

There are three post-run review surfaces.

### Diagnose one run

```bash
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose
```

Direct CLI:

```bash
edge operator diagnose --run_id <run_id>
```

Use when you need a structured explanation of why the run failed or why it is not promotable.

### Regime-report one run

```bash
make review RUN_ID=<run_id> REVIEW_ACTION=regime-report
```

Direct CLI:

```bash
edge operator regime-report --run_id <run_id>
```

Use when you need to know whether the strongest result survives or flips across regimes.

### Compare two or more runs

```bash
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
```

Direct CLI:

```bash
edge operator compare --run_ids <baseline_run,followup_run>
```

Use when the work is explicitly bounded against a prior slice or when you need time-slice comparisons.

## Decision logic after review

A run usually falls into one of five next actions.

- **repair** — fix mechanical or artifact issues first
- **confirm** — freeze the promising part and test an adjacent or bounded slice
- **kill/reframe** — the claim is not supported or the proposal was too broad
- **export** — the run is strong enough to become an explicit runtime thesis batch
- **package** — advanced bootstrap/governance work beyond the one-run export path

## Step 6 — export a thesis batch for runtime

Use export when one specific promoted run should become runtime-readable input.

```bash
make export RUN_ID=<run_id>
```

Direct module form:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
```

What export gives you:

- `data/live/theses/<run_id>/promoted_theses.json`
- `data/live/theses/index.json` as a catalog artifact
- a runtime batch tied to one explicit run lineage

Runtime should then be pointed at that batch explicitly using `strategy_runtime.thesis_path` or `strategy_runtime.thesis_run_id`.
If you need an explicit operator-managed bridge beyond raw export, the module surface also supports:

- `--register-runtime <name>` to record a named runtime registration in the thesis index
- `--set-deployment-state <thesis_id_or_candidate_id>=monitor_only|paper_only|live_enabled` for explicit deployment-state overrides

## Campaign workflow

Campaigns are a higher-level surface that repeatedly issue bounded proposals with mutation logic.

Entry point:

```bash
edge operator campaign start <campaign_spec.yaml> --plan_only 1
```

Use campaigns only when you already understand the single-proposal workflow. Campaigns build on the bounded operator path; they do not replace it.

## Proposal-side helper commands

Two additional proposal tools are useful before execution:

```bash
edge operator lint --proposal <proposal.yaml>
edge operator explain --proposal <proposal.yaml>
```

Use them when you need warnings on breadth or a compact view of resolved detectors, features, states, and run-all overrides.

## Strong operating rules

- Bound one mechanism slice at a time.
- Prefer plan before run.
- Prefer compare for confirmation work.
- Use diagnose before mutating the next proposal.
- Prefer explicit `export_promoted_theses --run_id <run_id>` before `make package` when your goal is runtime input from one bounded run.
- Move to `make package` only when you are trying to do broader thesis bootstrap/governance work rather than answer one bounded run question.
