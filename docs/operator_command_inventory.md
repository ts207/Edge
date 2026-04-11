# Command Inventory

Maintained against `project/cli.py` and `Makefile`.

This file is intentionally broader than the old name suggests. It covers:

- canonical lifecycle commands
- support-plane commands
- compatibility operator commands
- maintenance and validation targets

## Use These First

For day-to-day lifecycle work, prefer:

- `make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=plan|run`
- `make validate RUN_ID=<run_id>`
- `make promote RUN_ID=<run_id> SYMBOLS=BTCUSDT,ETHUSDT`
- `make export RUN_ID=<run_id>`
- `make deploy-paper RUN_ID=<run_id>`

Direct CLI equivalents:

- `python -m project.cli discover plan|run`
- `python -m project.cli validate run|report|diagnose`
- `python -m project.cli promote run|export`
- `python -m project.cli deploy list-theses|inspect-thesis|paper|live|status`

## Canonical Lifecycle Commands

### Discover

- `edge discover run --proposal <proposal.yaml>`
- `edge discover plan --proposal <proposal.yaml>`
- `edge discover list-artifacts --run_id <run_id>`

### Validate

- `edge validate run --run_id <run_id>`
- `edge validate report --run_id <run_id>`
- `edge validate diagnose --run_id <run_id>`
- `edge validate list-artifacts --run_id <run_id>`

### Promote

- `edge promote run --run_id <run_id> --symbols BTCUSDT,ETHUSDT`
- `edge promote export --run_id <run_id>`
- `edge promote list-artifacts --run_id <run_id>`

### Deploy

- `edge deploy list-theses`
- `edge deploy inspect-thesis --run_id <run_id>`
- `edge deploy paper --run_id <run_id> [--config <yaml>]`
- `edge deploy live --run_id <run_id> [--config <yaml>]`
- `edge deploy status`

## Support-Plane Commands

These are important, but they are not extra lifecycle stages.

### Ingest

- `edge ingest --run_id <run_id> --symbols BTCUSDT --start YYYY-MM-DD --end YYYY-MM-DD --exchange bybit --data_type ohlcv`

### Catalog

- `edge catalog list [--stage discover|validate|promote|deploy]`
- `edge catalog compare --run_id_a <run_a> --run_id_b <run_b> --stage discover|validate|promote`
- `edge catalog audit-artifacts [--run_id <run_id>] [--rewrite_stamps 1]`

### Advanced trigger discovery

- `edge discover triggers parameter-sweep ...`
- `edge discover triggers feature-cluster ...`
- `edge discover triggers report --proposal_dir <dir>`
- `edge discover triggers emit-registry-payload --candidate_id <id> --proposal_dir <dir>`
- `edge discover triggers list`
- `edge discover triggers inspect --candidate_id <id>`
- `edge discover triggers review --candidate_id <id>`
- `edge discover triggers approve --candidate_id <id>`
- `edge discover triggers reject --candidate_id <id> --reason <text>`
- `edge discover triggers mark-adopted --candidate_id <id>`

## Compatibility Operator Commands

> [!WARNING]
> `edge operator ...` is still supported, but it is a compatibility surface. New documentation should teach the stage verbs first.

Current `operator` commands:

- `edge operator preflight`
- `edge operator plan`
- `edge operator run`
- `edge operator lint`
- `edge operator explain`
- `edge operator compare`
- `edge operator regime-report`
- `edge operator diagnose`
- `edge operator campaign start`

Current conceptual mapping:

| Compatibility command | Preferred surface |
|-----------------------|-------------------|
| `operator preflight` | discover planning / proposal validation |
| `operator plan` | `discover plan` |
| `operator run` | `discover run` |
| `operator regime-report` | `validate report` |
| `operator diagnose` | `validate diagnose` |
| `operator compare` | `catalog compare` or validation/report review depending on need |

## Deprecated Pipeline Command

Still present:

- `edge pipeline run-all`

This is a compatibility orchestration command, not the canonical lifecycle front door.

## Make Targets

### Canonical lifecycle wrappers

- `discover`
- `validate`
- `promote`
- `export`
- `deploy-paper`

### Review and maintenance wrappers

- `review`
- `legacy-validate`
- `governance`
- `minimum-green-gate`
- `test`
- `test-fast`
- `lint`
- `format`
- `format-check`
- `style`
- `pre-commit`

### Advanced workflow bundles

- `run`
- `baseline`
- `discover-blueprints`
- `discover-edges`
- `discover-edges-from-raw`
- `discover-target`
- `discover-concept`
- `golden-workflow`
- `golden-synthetic-discovery`
- `golden-certification`
- `synthetic-demo`
- `package`

### Benchmark and hygiene targets

- `benchmark-maintenance-smoke`
- `benchmark-maintenance`
- `benchmark-m0`
- `bench-pipeline`
- `check-hygiene`
- `clean`
- `clean-all-data`
- `clean-hygiene`
- `clean-repo`
- `clean-run-data`
- `clean-runtime`
- `debloat`
- `compile`

## Maintenance Script Inventory

The repo-local plugin wrappers under `plugins/edge-agents/scripts/` are important for maintenance and operator support. The main ones are:

- `edge_preflight_proposal.sh`
- `edge_plan_proposal.sh`
- `edge_run_proposal.sh`
- `edge_lint_proposal.sh`
- `edge_explain_proposal.sh`
- `edge_diagnose_run.sh`
- `edge_regime_report.sh`
- `edge_compare_runs.sh`
- `edge_export_theses.sh`
- `edge_validate_repo.sh`
- `edge_verify_contracts.sh`
- `edge_governance.sh`
- `edge_chatgpt_app.sh`
- `edge_sync_plugin.sh`

Use these as wrappers around canonical repo surfaces, not as replacement policy layers.
