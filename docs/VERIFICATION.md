# Researcher Verification

## Default Entry Point

Use the maintained verification script:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification --mode contracts
```

For a completed bounded run:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification \
  --mode experiment \
  --run-id <run_id>
```

Optional baseline comparison:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification \
  --mode experiment \
  --run-id <run_id> \
  --baseline-run-id <baseline_run_id>
```

## After Any Code Change

Run:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification --mode contracts
```

This block currently enforces:

- regime-routing audit through `project/scripts/regime_routing_audit.py --check`
- proposal-schema coverage
- regime-routing tests
- regime metadata annotation tests
- phase-5 contract tests
- promotion artifact schema tests
- regime-first frontier tests
- proposal issuance memory-audit tests

## After Any Schema Or Config Change

Run the same contract block:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification --mode contracts
```

Then inspect whether the changed file is one of the forbidden contract surfaces in `agent_operating_contract.md`. If yes, stop and escalate instead of continuing.

## After Any Bounded Experiment

Run:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification \
  --mode experiment \
  --run-id <run_id>
```

This block currently requires:

- the contract block above,
- `data/runs/<run_id>/run_manifest.json`,
- `data/reports/phase2/<run_id>/phase2_candidates.parquet`,
- `data/reports/phase2/<run_id>/phase2_diagnostics.json`,
- valid current-format phase-2 schema,
- a complete promotion bundle under `data/reports/promotions/<run_id>/`,
- optional run comparison if a baseline run is supplied.

## After Any Local Defect Fix

Run:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification --mode contracts
```

If the fix was triggered by a specific run, also run:

```bash
.venv/bin/python -m project.scripts.run_researcher_verification \
  --mode experiment \
  --run-id <run_id>
```

## Explicit Stop Conditions

Stop immediately if any verification block:

- returns non-zero,
- reports missing artifacts,
- reports schema failure,
- reports invalid regime routing,
- or produces a comparison failure against the intended baseline.

When a block fails:

- classify the issue as `repair`, `hold`, or `kill`,
- write the failure into the experiment review,
- do not start a new experiment until the failure is resolved or escalated.
