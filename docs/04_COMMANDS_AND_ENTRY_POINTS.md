# Commands and entry points

Use the highest-level surface that does exactly what you need.

Preferred order:

1. `make discover|review|export|validate`
2. `edge operator ...`
3. direct module or console-script surfaces
4. `make package` only for advanced bootstrap maintenance
5. individual maintenance scripts under `project/scripts/`

## Canonical operator surfaces

Proposal inspection and execution:

```bash
edge operator explain --proposal <proposal.yaml>
edge operator preflight --proposal <proposal.yaml>
edge operator plan --proposal <proposal.yaml>
edge operator run --proposal <proposal.yaml>
edge operator lint --proposal <proposal.yaml>
```

Run review:

```bash
edge operator diagnose --run_id <run_id>
edge operator regime-report --run_id <run_id>
edge operator compare --run_ids <run_a,run_b>
```

Campaign surface:

```bash
edge operator campaign start <campaign_spec.yaml> --plan_only 1
```

Campaigns are higher-order wrappers around the bounded operator path. Learn the single-proposal path first.

## Canonical make aliases

```bash
make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight|plan|run
make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|regime-report
make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>
make export RUN_ID=<run_id>
make validate
```

These are the shortest teaching surface for a new operator.

## Task-to-command map

You want to understand how a proposal normalizes:

```bash
edge operator explain --proposal <proposal.yaml>
```

You want to know whether a proposal is locally runnable:

```bash
edge operator preflight --proposal <proposal.yaml>
```

You want the exact experiment bundle without executing:

```bash
edge operator plan --proposal <proposal.yaml>
```

You want a durable run:

```bash
edge operator run --proposal <proposal.yaml>
```

You already have a run and want diagnosis:

```bash
edge operator diagnose --run_id <run_id>
```

You want regime sensitivity:

```bash
edge operator regime-report --run_id <run_id>
```

You want a bounded baseline comparison:

```bash
edge operator compare --run_ids <baseline_run,followup_run>
```

You want a runtime thesis batch from one run:

```bash
make export RUN_ID=<run_id>
```

You want repo-level contract validation:

```bash
make validate
python -m project.scripts.run_researcher_verification --mode contracts
```

## Canonical export bridge

Module form:

```bash
python -m project.research.export_promoted_theses --run_id <run_id>
```

Optional explicit runtime registration and deployment-state controls:

```bash
python -m project.research.export_promoted_theses \
  --run_id <run_id> \
  --register-runtime <name> \
  --set-deployment-state <thesis_id_or_candidate_id>=live_enabled
```

This is the canonical way to turn one run into one runtime thesis batch.

## Lower-level pipeline surfaces

Use these only when you intentionally need control beyond the operator path.

Full pipeline:

```bash
edge-run-all --run_id <run_id> --symbols BTCUSDT --start 2025-01-01 --end 2025-01-31
python -m project.pipelines.run_all ...
```

Other stable console scripts:

```bash
edge-phase2-discovery
edge-promote
compile-strategy-blueprints
build-strategy-candidates
edge-live-engine
edge-smoke
backtest
edge-backtest
```

## Advanced maintenance surfaces

Bootstrap/package maintenance:

```bash
make package
python -m project.scripts.build_seed_bootstrap_artifacts
python -m project.scripts.build_seed_testing_artifacts
python -m project.scripts.build_seed_empirical_artifacts
python -m project.scripts.build_founding_thesis_evidence
python -m project.scripts.build_seed_packaging_artifacts
python -m project.scripts.build_structural_confirmation_artifacts
python -m project.scripts.build_thesis_overlap_artifacts --run_id <run_id>
./project/scripts/regenerate_artifacts.sh
```

These are real, but they are not the preferred surface for day-to-day operator work.

## Common misuse

- teaching `run_all` before `edge operator`
- teaching legacy proposal-shape details before the single-hypothesis front door
- treating bootstrap scripts as the normal export path
- treating `data/live/theses/index.json` as a runtime selector instead of a catalog
