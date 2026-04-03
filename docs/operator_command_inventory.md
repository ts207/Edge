# Operator command inventory

Generated from `project/cli.py` and `Makefile`. Update this file with `python -m project.scripts.generate_operator_surface_inventory`.

## Preferred front door

Use these surfaces first:

- `edge operator preflight|plan|run` for bounded research issuance
- thesis bootstrap builders for `package` and thesis-store refresh
- `edge operator diagnose|regime-report|compare` for post-run review
- maintained `make` targets only for common workflow bundles and maintenance

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

## Make targets

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
- `pre-commit`
- `run`
- `style`
- `synthetic-demo`
- `test`
- `test-fast`

## Inventory payload

```json
{
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
    "pre-commit",
    "run",
    "style",
    "synthetic-demo",
    "test",
    "test-fast"
  ]
}
```
