# Edge

Edge is an event-driven trading research and backtest repository. The current canonical path is:

`ingest -> build_cleaned -> build_features -> context -> event analysis -> phase2 discovery -> promotion -> strategy packaging`

The repo is centered on:

- `project/pipelines/run_all.py` for orchestration
- `project/contracts/pipeline_registry.py` for stage and artifact contracts
- `project/pipelines/features/build_features.py` for canonical feature generation
- `project/research/services/` for typed research workflow execution
- `project/pipelines/research/cli/` for research CLI parsing and `argv -> config`
- `project/research/compat/` for research-owned helper surfaces still used by tests and scripts
- `project/reliability/cli_smoke.py` for deterministic smoke runs

## Current Canonical Conventions

- Feature stage names are `build_features_{timeframe}` and `build_features_{timeframe}_spot`
- Feature artifact tokens are `features.perp.v2` and `features.spot.v2`
- On-disk feature datasets live under `features_feature_schema_v2`
- Feature schema selection is effectively `v2` only
- Detector loading is explicit through `project/events/detectors/catalog.py` and `project/events/detectors/registry.py`
- Detector ownership config and runtime registry are expected to stay aligned; regenerate `docs/generated/detector_coverage.*` after detector inventory changes
- Event family logic is split by responsibility:
  - `project/events/detectors/` for detector classes
  - `project/events/registries/` for registration maps
  - `project/events/adapters/` for analyzer dispatch
  - `project/events/families/` for compatibility facades

## Install

```bash
pip install -e .
```

Optional extra:

```bash
pip install -e ".[nautilus]"
```

## Main Entry Points

Run a planned or full pipeline:

```bash
edge-run-all --run_id demo_run --symbols BTCUSDT --start 2024-01-01 --end 2024-01-31 --plan_only 1
```

Run a deterministic smoke workflow:

```bash
edge-smoke --mode research
```

Inspect or launch the live engine with durable state:

```bash
edge-live-engine --config project/configs/golden_certification.yaml --print_session_metadata
edge-live-engine --config project/configs/golden_certification.yaml --snapshot_path artifacts/live_state.json
```

A checked-in `systemd` template is available at `deploy/systemd/edge-live-engine.service`.
Environment-specific units are also available at `deploy/systemd/edge-live-engine-paper.service` and `deploy/systemd/edge-live-engine-production.service`.
Matching environment file templates are available at `deploy/env/edge-live-engine-paper.env.example` and `deploy/env/edge-live-engine-production.env.example`.

Run a targeted single-event discovery chain:

```bash
make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK
```

Run the synthetic discovery workflow:

```bash
python3 -m project.scripts.run_golden_synthetic_discovery
```

Generate a curated synthetic dataset suite for agent-driven research:

```bash
python3 -m project.scripts.generate_synthetic_crypto_regimes --suite_config project/configs/synthetic_dataset_suite.yaml --run_id synthetic_suite
```

Validate detector outputs against the synthetic truth map:

```bash
python3 -m project.scripts.validate_synthetic_detector_truth --run_id golden_synthetic_discovery
```

## Repository Layout

- `project/`: application code
- `docs/`: maintained high-level documentation
- `spec/`: ontology, runtime, search, and strategy specs
- `tests/`: regression, contract, smoke, and architecture coverage
- `data/`: local run outputs when using the default data root

## Documentation

- [Claude Code Guide](CLAUDE.md)
- [Agent Research Docs](docs/README.md)
- [Synthetic Datasets](docs/SYNTHETIC_DATASETS.md)
- [Autonomous Research Loop](docs/AUTONOMOUS_RESEARCH_LOOP.md)
- [Experiment Protocol](docs/EXPERIMENT_PROTOCOL.md)
- [Memory And Reflection](docs/MEMORY_AND_REFLECTION.md)
- [Operations And Guardrails](docs/OPERATIONS_AND_GUARDRAILS.md)
- [Contributing](CONTRIBUTING.md)

## Claude Code Quickstart

The repo is now prepared for Claude Code as the external controller. The shortest safe path is:

1. inspect core knobs
2. inspect campaign memory
3. issue a narrow proposal with `plan_only`

Examples:

```bash
.venv/bin/python -m project.research.knowledge.query knobs
.venv/bin/python -m project.research.knowledge.query memory --program_id btc_campaign
.venv/bin/python -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

Use [CLAUDE.md](CLAUDE.md) as the repo-specific operating guide.
