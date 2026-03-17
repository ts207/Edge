# Contributing

## Development Setup

Install the package in editable mode:

```bash
pip install -e .
```

Use the repository virtualenv if present. The codebase assumes Python 3.11+.

## Workflow

1. Make changes in the canonical path, not compatibility wrappers.
2. Keep pipeline names, contracts, and tests aligned.
3. Add or update regression coverage for any behavior change.
4. Prefer service-owned workflow changes over CLI-owned orchestration changes.

## Current Project Conventions

- The canonical feature builder is `project/pipelines/features/build_features.py`
- Feature schema is `v2`
- Canonical feature artifacts are `features.perp.v2` and `features.spot.v2`
- `project/contracts` and `project/research` should not grow new dependencies on `project.pipelines`
- Detector registration is explicit, not import-side-effect driven

## Useful Commands

Plan a run:

```bash
edge-run-all --run_id local_plan --symbols BTCUSDT --start 2024-01-01 --end 2024-01-07 --plan_only 1
```

Run fast smoke coverage:

```bash
edge-smoke --mode research
```

Inspect the live bootstrap contract:

```bash
edge-live-engine --config project/configs/golden_certification.yaml --print_session_metadata
```

Run tests:

```bash
pytest -q
```

Lint:

```bash
python -m ruff check .
```

Format:

```bash
python -m ruff format .
```

## Documentation Rule

If you rename stages, artifact tokens, schemas, or entrypoints, update:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PIPELINE.md`
- `docs/RESEARCH_WORKFLOW.md`
- any local README in the affected subsystem
