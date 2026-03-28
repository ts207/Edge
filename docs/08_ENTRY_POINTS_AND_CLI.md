# Entry Points and CLI

## Installed Console Scripts

Defined in `pyproject.toml`:

- `backtest`
- `edge-backtest`
- `edge-run-all`
- `edge-live-engine`
- `edge-phase2-discovery`
- `edge-promote`
- `edge-smoke`
- `compile-strategy-blueprints`
- `build-strategy-candidates`
- `ontology-consistency-audit`

## Canonical Orchestrator

The main orchestrator is:

```bash
edge-run-all --run_id demo --symbols BTCUSDT --start 2024-01-01 --end 2024-03-31 --plan_only 1
```

Equivalent Python module form:

```bash
python -m project.pipelines.run_all --run_id demo --symbols BTCUSDT --start 2024-01-01 --end 2024-03-31 --plan_only 1
```

## `backtest` / `edge-backtest`

`project/cli.py` exposes:

- `pipeline run-all`
- `ingest`

Examples:

```bash
backtest pipeline run-all --run_id demo --symbols BTCUSDT --start 2024-01-01 --end 2024-03-31
backtest ingest --run_id ingest_demo --symbols BTCUSDT --start 2024-01-01 --end 2024-01-31 --timeframe 5m
```

Use `edge-run-all` directly when you want the full modern run surface. The compatibility CLI is thinner.

## Proposal and Planning CLIs

Main proposal tooling:

```bash
python -m project.research.agent_io.proposal_to_experiment --proposal /abs/path/to/proposal.yaml --registry_root project/configs/registries
python -m project.research.agent_io.execute_proposal --proposal /abs/path/to/proposal.yaml --run_id run_001 --registry_root project/configs/registries --out_dir /tmp/run_001 --plan_only 1
python -m project.research.agent_io.issue_proposal --proposal /abs/path/to/proposal.yaml --registry_root project/configs/registries --plan_only 1
```

Responsibilities:

- `proposal_to_experiment`
  - translate proposal and emit validated config / overrides
- `execute_proposal`
  - translate and invoke `run_all`
- `issue_proposal`
  - same as above plus memory bookkeeping and run-id issuance

## Smoke and Reliability CLI

```bash
edge-smoke --mode research
edge-smoke --mode full --root /tmp/edge-smoke
edge-smoke --mode validate-artifacts --root /path/to/artifacts/root
```

Supported modes:

- `engine`
- `research`
- `promotion`
- `full`
- `validate-artifacts`

This CLI both generates smoke artifacts and validates artifact contracts.

## Live Engine CLI

```bash
edge-live-engine --config project/configs/golden_certification.yaml --print_session_metadata
edge-live-engine --config project/configs/live_paper.yaml --snapshot_path artifacts/live_state.json
```

The live runtime validates:

- environment variables
- config / snapshot alignment
- Binance venue connectivity
- account snapshot normalization

## `run_all` Flag Families

`project.pipelines.pipeline_planning.build_parser()` currently exposes a wide run surface. Treat the flags in groups:

### Identity and scope

- `--run_id`
- `--symbols`
- `--start`
- `--end`
- `--timeframes`
- `--program_id`
- `--concept`

### Config layering

- `--experiment_config`
- `--registry_root`
- `--config`
- `--override`

### Ingest and data-path controls

- `--skip_ingest_ohlcv`
- `--skip_ingest_funding`
- `--skip_ingest_spot_ohlcv`
- `--run_ingest_liquidation_snapshot`
- `--run_ingest_open_interest_hist`
- `--funding_scale`
- `--enable_cross_venue_spot_pipeline`

### Discovery scope

- `--events`
- `--templates`
- `--contexts`
- `--horizons`
- `--directions`
- `--entry_lags`
- `--phase2_event_type`
- `--discovery_profile`
- `--search_spec`

### Research quality and promotion

- `--run_candidate_promotion`
- `--candidate_promotion_profile`
- `--run_recommendations_checklist`
- `--run_expectancy_analysis`
- `--run_expectancy_robustness`
- `--run_edge_registry_update`
- `--run_campaign_memory_update`

### Strategy packaging

- `--run_strategy_builder`
- `--run_strategy_blueprint_compiler`
- `--run_profitable_selector`

### Runtime and reproducibility

- `--runtime_invariants_mode`
- `--determinism_replay_checks`
- `--oms_replay_checks`
- `--emit_run_hash`
- `--resume_from_failed_stage`
- `--dry_run`
- `--plan_only`

### Research comparison drift thresholds

Flags prefixed with `--research_compare_*` govern tolerated drift for:

- phase2 candidate counts
- survivor counts
- promoted counts
- edge candidate counts
- cost medians
- expectancy medians

These defaults are part of the repo's research-calibration behavior, not cosmetic CLI noise.

## Maintained `make` Targets

Important targets:

- `make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK`
- `make discover-concept CONCEPT=<concept>`
- `make discover-edges`
- `make discover-blueprints`
- `make run`
- `make baseline`
- `make golden-workflow`
- `make golden-synthetic-discovery`
- `make golden-certification`
- `make benchmark-maintenance-smoke`
- `make benchmark-maintenance`
- `make minimum-green-gate`
- `make test`
- `make test-fast`
- `make lint`
- `make format-check`

## High-Value Scripts

Frequently used scripts under `project/scripts/`:

- `run_golden_workflow.py`
- `run_golden_regression.py`
- `run_certification_workflow.py`
- `run_golden_synthetic_discovery.py`
- `run_fast_synthetic_certification.py`
- `validate_synthetic_detector_truth.py`
- `run_benchmark_maintenance_cycle.py`
- `show_benchmark_review.py`
- `show_promotion_readiness.py`
- `build_system_map.py`
- `build_architecture_metrics.py`
- `detector_coverage_audit.py`
- `ontology_consistency_audit.py`
- `build_event_ontology_artifacts.py`
- `event_ontology_audit.py`
- `regime_routing_audit.py`

Use these instead of inventing ad hoc maintenance commands.
