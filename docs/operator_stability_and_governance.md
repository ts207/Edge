# Operator stability and governance

The default operator surface is bounded experiments plus explicit run export.
Bootstrap governance remains an advanced maintainer lane.

## Bounded experiment review surfaces

Operator-facing review surfaces include:

1. `edge operator compare --run_ids <run_a,run_b,...>`
   - builds a compact time-slice comparison report
   - classifies the effect as `stable`, `concentrated`, `mixed`, `weak`, or `absent`
2. `edge operator regime-report --run_id <run_id>`
   - inspects leading candidate rows for regime sign flips and stability warnings
3. `edge operator diagnose --run_id <run_id>`
   - writes structured negative-result diagnostics
   - classifies the main blocker as:
     - `mechanical_artifact_gap`
     - `low_sample_power`
     - `regime_instability`
     - `no_effect`

Artifacts land under `data/reports/operator/`:

- `time_slice_report/<slug>/`
- `regime_split_report/<run_id>/`
- `negative_result_diagnostics/<run_id>/`

## Advanced bootstrap governance surfaces

If you are maintaining bootstrap artifacts, inspect:

- `docs/generated/promotion_seed_inventory.*`
- `docs/generated/thesis_testing_scorecards.*`
- `docs/generated/thesis_empirical_scorecards.*`
- `docs/generated/seed_thesis_catalog.md`
- `docs/generated/seed_thesis_packaging_summary.*`
- `docs/generated/thesis_overlap_graph.*`

These tell you:

- which theses are queued
- which ones still need repair or evidence
- which ones are packaged
- whether the packaged set is structurally disconnected or overlap-aware

## Typical bounded follow-up loop

Use the canonical sequence:

1. `edge operator preflight --proposal <proposal.yaml>`
2. `edge operator plan --proposal <proposal.yaml>`
3. `edge operator run --proposal <proposal.yaml>`
4. `edge operator diagnose --run_id <run_id>`
5. `edge operator regime-report --run_id <run_id>`
6. `edge operator compare --run_ids <baseline_run,followup_run>`

Then, if the result should become a runtime batch, export it from that run directly:

```bash
make export RUN_ID=<run_id>
```

Only switch to the bootstrap lane when you are intentionally maintaining seed / empirical / packaging artifacts.

## Governance surfaces

The repo keeps lightweight governance around the canonical operator path:

- `project/scripts/generate_operator_surface_inventory.py`
  - regenerates `docs/operator_command_inventory.md`
- tests that keep the command inventory aligned with `project/cli.py`
- tests that keep `README.md` and `docs/00_START_HERE.md` anchored to the canonical operator flow
- bootstrap artifact builders collected under `project/scripts/regenerate_artifacts.sh`

Regenerate the operator inventory after command-surface changes with:

```bash
python -m project.scripts.generate_operator_surface_inventory
```

Regenerate the broader bootstrap artifact surfaces with:

```bash
./project/scripts/regenerate_artifacts.sh
```
