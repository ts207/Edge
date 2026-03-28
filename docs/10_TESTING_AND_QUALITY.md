# Testing and Quality

## Local Baseline Commands

The maintained local quality commands are:

```bash
make test
make test-fast
make lint
make format-check
make minimum-green-gate
```

Meaning:

- `test`
  - full pytest suite
- `test-fast`
  - `pytest -q -m "not slow" --maxfail=1`
- `lint`
  - Ruff lint on changed Python files
- `format-check`
  - Ruff format check on changed Python files
- `minimum-green-gate`
  - structural checks + generated audit drift + golden regression + golden workflow

## CI Tiers

### Tier 1: Structural Fast Gate

Defined in `.github/workflows/tier1.yml`.

It runs:

- compile check
- architecture tests
- spec validation CLI
- ontology consistency drift
- detector coverage drift
- system-map drift
- selected fast regression tests
- Pyright

This is the quickest broad structural confidence layer.

### Tier 2: Deterministic Workflow Gate

Defined in `.github/workflows/tier2.yml`.

It runs:

- research smoke
- promotion smoke
- engine smoke
- full smoke CLI workflow
- determinism/replay/runtime postflight tests
- manifest/provenance assertions

This is where workflow correctness and reproducibility are tested more directly.

### Tier 3: Broad Correctness Gate

Defined in `.github/workflows/tier3.yml`.

It runs:

- full pytest
- replay and regression suites
- larger integration / pipeline tests

This is the broadest correctness surface.

## Test Suite Layout

The repo's tests are intentionally partitioned by concern.

Key directories under `project/tests/`:

- `architecture/`
- `artifacts/`
- `contracts/`
- `docs/`
- `domain/`
- `engine/`
- `eval/`
- `events/`
- `features/`
- `live/`
- `pipelines/`
- `pit/`
- `regressions/`
- `reliability/`
- `replays/`
- `research/`
- `runtime/`
- `smoke/`
- `spec_registry/`
- `spec_validation/`
- `strategy/`
- `strategy_dsl/`
- `strategy_templates/`
- `synthetic_truth/`

Do not describe the test suite as only "unit and integration tests." The partitioning is more deliberate than that.

## Artifact Drift and Generated Docs

Quality includes generated-doc drift checks.

The current structural maintenance surface includes:

- `project/scripts/detector_coverage_audit.py`
- `project/scripts/ontology_consistency_audit.py`
- `project/scripts/build_system_map.py`
- `project/scripts/build_architecture_metrics.py`
- `project/scripts/build_event_ontology_artifacts.py`
- `project/scripts/event_ontology_audit.py`
- `project/scripts/regime_routing_audit.py`

Generated outputs under `docs/generated/` are part of the quality model.

## Smoke and Regression Workflows

Smoke correctness is tested through:

- smoke pytest modules
- `project.reliability.cli_smoke`
- golden workflow
- golden regression

Important scripts:

- `project/scripts/run_golden_workflow.py`
- `project/scripts/run_golden_regression.py`
- `project/scripts/run_certification_workflow.py`

## Runtime and Replay Quality

The repository has explicit runtime correctness surfaces:

- runtime hashing
- runtime postflight
- determinism replay
- OMS replay

This is why runtime and replay tests have dedicated CI coverage and directory partitions.

## Research Drift and Calibration

Research quality is not only about whether a test passes. It also includes controlled drift behavior for candidate and promotion outputs.

Relevant controls exist in `run_all` flags prefixed with `--research_compare_*`, and the baseline narrative lives in `docs/RESEARCH_CALIBRATION_BASELINE.md`.

## Documentation Quality

There is a docs test today for the research calibration baseline. More importantly, docs should align with:

- code paths that exist
- commands that exist
- generated docs that exist
- CI behavior that exists

When in doubt:

1. trust the workflow YAML
2. trust the code
3. trust generated artifacts
4. then fix the docs
