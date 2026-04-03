# Operator command inventory

Generated from `project/cli.py` and `Makefile`. Update this file with `python -m project.scripts.generate_operator_surface_inventory`.

## Preferred front door

Use these surfaces first:

- `make discover PROPOSAL=<proposal.yaml> DISCOVER_ACTION=preflight|plan|run`
- `make export RUN_ID=<run_id>`
- `make validate`
- `make review RUN_ID=<run_id> REVIEW_ACTION=diagnose|regime-report`
- `make review REVIEW_ACTION=compare RUN_IDS=<baseline_run,followup_run>`

Treat `make package` as an advanced bootstrap/governance surface, not the default way to produce a runtime thesis batch.

Direct CLI equivalents:

- `edge operator preflight|plan|run` for bounded research issuance
- `edge operator diagnose|regime-report|compare` for post-run review
- `python -m project.research.export_promoted_theses --run_id <run_id>` for explicit thesis-batch export

## Canonical operator commands

- `edge operator campaign`
- `edge operator compare`
- `edge operator diagnose`
- `edge operator explain`
- `edge operator lint`
- `edge operator plan`
- `edge operator preflight`
- `edge operator regime-report`
- `edge operator run`

## Operator action targets

- `discover`
- `export`
- `validate`
- `review`

## Advanced / maintenance make targets

- `baseline`
- `bench-pipeline`
- `benchmark-m0`
- `benchmark-maintenance`
- `benchmark-maintenance-smoke`
- `check-hygiene`
- `clean`
- `clean-all-data`
- `clean-hygiene`
- `clean-repo`
- `clean-run-data`
- `clean-runtime`
- `compile`
- `debloat`
- `discover-blueprints`
- `discover-concept`
- `discover-edges`
- `discover-edges-from-raw`
- `discover-hybrid`
- `discover-target`
- `format`
- `format-check`
- `golden-certification`
- `golden-synthetic-discovery`
- `golden-workflow`
- `governance`
- `help`
- `lint`
- `minimum-green-gate`
- `monitor`
- `package`
- `pre-commit`
- `run`
- `style`
- `synthetic-demo`
- `test`
- `test-fast`

## Inventory payload

```json
{
  "advanced_make_targets": [
    "baseline",
    "bench-pipeline",
    "benchmark-m0",
    "benchmark-maintenance",
    "benchmark-maintenance-smoke",
    "check-hygiene",
    "clean",
    "clean-all-data",
    "clean-hygiene",
    "clean-repo",
    "clean-run-data",
    "clean-runtime",
    "compile",
    "debloat",
    "discover-blueprints",
    "discover-concept",
    "discover-edges",
    "discover-edges-from-raw",
    "discover-hybrid",
    "discover-target",
    "format",
    "format-check",
    "golden-certification",
    "golden-synthetic-discovery",
    "golden-workflow",
    "governance",
    "help",
    "lint",
    "minimum-green-gate",
    "monitor",
    "package",
    "pre-commit",
    "run",
    "style",
    "synthetic-demo",
    "test",
    "test-fast"
  ],
  "canonical_operator_commands": [
    "edge operator campaign",
    "edge operator compare",
    "edge operator diagnose",
    "edge operator explain",
    "edge operator lint",
    "edge operator plan",
    "edge operator preflight",
    "edge operator regime-report",
    "edge operator run"
  ],
  "make_targets": [
    "baseline",
    "bench-pipeline",
    "benchmark-m0",
    "benchmark-maintenance",
    "benchmark-maintenance-smoke",
    "check-hygiene",
    "clean",
    "clean-all-data",
    "clean-hygiene",
    "clean-repo",
    "clean-run-data",
    "clean-runtime",
    "compile",
    "debloat",
    "discover",
    "discover-blueprints",
    "discover-concept",
    "discover-edges",
    "discover-edges-from-raw",
    "discover-hybrid",
    "discover-target",
    "export",
    "format",
    "format-check",
    "golden-certification",
    "golden-synthetic-discovery",
    "golden-workflow",
    "governance",
    "help",
    "lint",
    "minimum-green-gate",
    "monitor",
    "package",
    "pre-commit",
    "review",
    "run",
    "style",
    "synthetic-demo",
    "test",
    "test-fast",
    "validate"
  ],
  "operator_action_targets": [
    "discover",
    "export",
    "validate",
    "review"
  ]
}
```
