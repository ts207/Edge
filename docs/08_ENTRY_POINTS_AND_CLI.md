# Edge — Entry Points & CLI Reference

## Installed CLI Commands

Registered in `pyproject.toml` `[project.scripts]`:

| Command | Entry Point | Role |
|---|---|---|
| `edge-run-all` | `project.pipelines.run_all:main` | **Primary**: Full pipeline orchestration |
| `edge-phase2-discovery` | `project.pipelines.research.phase2_candidate_discovery:main` | Phase 2 discovery only |
| `edge-promote` | `project.pipelines.research.promote_candidates:main` | Promotion pass only |
| `edge-live-engine` | `project.scripts.run_live_engine:main` | Live trading engine |
| `edge-backtest` / `backtest` | `project.cli:main` | Backtest runner |
| `edge-smoke` | `project.reliability.cli_smoke:main` | Smoke test runner |
| `compile-strategy-blueprints` | `project.pipelines.research.compile_strategy_blueprints:main` | Blueprint compilation |
| `build-strategy-candidates` | `project.pipelines.research.build_strategy_candidates:main` | Strategy candidate assembly |
| `ontology-consistency-audit` | `project.scripts.ontology_consistency_audit:main` | Ontology audit |

---

## `edge-run-all` — Full Pipeline CLI

The primary entry point. All flags:

### Required

```
--run_id         <str>    Unique identifier for this run
--symbols        <str>    Comma-separated symbols, e.g. BTCUSDT,ETHUSDT
--start          <date>   Start date (YYYY-MM-DD)
--end            <date>   End date (YYYY-MM-DD)
```

### Planning

```
--plan_only      <0|1>    Plan and print the run without executing [default: 0]
```

### Timeframes

```
--timeframes     <str>    Comma-separated timeframes [default: 5m]
```

### Phase 2 Controls

```
--run_phase2_conditional  <0|1>  Run phase 2 hypothesis evaluation [default: 1]
--phase2_event_type       <str>  Filter to single event type (targeted runs)
--concept                 <str>  Concept filter for discovery
```

### Pipeline Stage Switches

```
--run_edge_candidate_universe  <0|1>  Run edge candidate universe [default: 1]
--run_strategy_builder         <0|1>  Build strategy candidates [default: 1]
--run_recommendations_checklist <0|1> Generate checklist [default: 1]
--enable_cross_venue_spot_pipeline <0|1> Include spot pipeline [default: 0]
```

### Usage Examples

```bash
# Full pipeline on BTC+ETH
edge-run-all \
  --run_id btc_eth_2024q1 \
  --symbols BTCUSDT,ETHUSDT \
  --start 2024-01-01 \
  --end 2024-03-31

# Plan first (safe preview)
edge-run-all \
  --run_id btc_eth_2024q1 \
  --symbols BTCUSDT,ETHUSDT \
  --start 2024-01-01 \
  --end 2024-03-31 \
  --plan_only 1

# Targeted single event
edge-run-all \
  --run_id vol_shock_run \
  --symbols BTCUSDT \
  --start 2024-01-01 \
  --end 2024-06-30 \
  --run_phase2_conditional 1 \
  --phase2_event_type VOL_SHOCK \
  --run_strategy_builder 0 \
  --run_recommendations_checklist 0

# Features-only (no discovery)
edge-run-all \
  --run_id features_prep \
  --symbols BTCUSDT \
  --start 2024-01-01 \
  --end 2024-03-31 \
  --run_phase2_conditional 0 \
  --run_edge_candidate_universe 0 \
  --run_strategy_builder 0
```

---

## `edge-phase2-discovery` — Phase 2 Only

Runs discovery on previously prepared data (requires completed ingest+clean+features run).

```bash
edge-phase2-discovery --run_id <existing_run_id>
```

---

## `edge-promote` — Promotion Pass

Runs the promotion stage on a completed discovery run.

```bash
edge-promote --run_id <run_id_with_discovery>
```

---

## `edge-live-engine` — Live Engine

```bash
# Print session metadata (safe inspect)
edge-live-engine \
  --config project/configs/golden_certification.yaml \
  --print_session_metadata

# Launch with state snapshot
edge-live-engine \
  --config project/configs/golden_certification.yaml \
  --snapshot_path artifacts/live_state.json

# Launch (no snapshot)
edge-live-engine \
  --config project/configs/golden_certification.yaml
```

---

## `edge-smoke` — Smoke Test

```bash
edge-smoke
```

Runs the reliability smoke test suite. Validates the system can initialize and run a minimal pipeline without errors.

---

## Knowledge Query CLI (`project.research.knowledge.query`)

```bash
# List all tunable knobs
python3 -m project.research.knowledge.query knobs

# Read campaign memory
python3 -m project.research.knowledge.query memory \
  --program_id btc_campaign

# Read static knowledge about an event
python3 -m project.research.knowledge.query static \
  --event BASIS_DISLOC

# Read static knowledge about a feature
python3 -m project.research.knowledge.query static \
  --feature vol_regime
```

---

## Agent I/O CLI

### `proposal_to_experiment`

Translates a compact proposal YAML to repo-native experiment config:

```bash
python3 -m project.research.agent_io.proposal_to_experiment \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json
```

### `execute_proposal`

Plan or execute a proposal directly:

```bash
# Plan only
python3 -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_basis_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_basis_001 \
  --plan_only 1

# Execute
python3 -m project.research.agent_io.execute_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --run_id btc_basis_001 \
  --registry_root project/configs/registries \
  --out_dir data/artifacts/experiments/btc_campaign/proposals/btc_basis_001
```

### `issue_proposal`

Issues a proposal with memory bookkeeping (preferred over `execute_proposal` for campaigns):

```bash
python3 -m project.research.agent_io.issue_proposal \
  --proposal /abs/path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

---

## Maintenance Scripts (`python3 -m project.scripts.*`)

| Command | Purpose |
|---|---|
| `python3 -m project.scripts.build_system_map --check` | Regenerate system map, fail if drift detected |
| `python3 -m project.scripts.detector_coverage_audit --md-out ... --json-out ... --check` | Regenerate detector coverage, fail on drift |
| `python3 -m project.scripts.ontology_consistency_audit --output ... --check` | Regenerate ontology audit, fail on drift |
| `python3 -m project.scripts.build_architecture_metrics --check` | Regenerate architecture metrics |
| `python3 -m project.scripts.run_golden_synthetic_discovery` | Golden synthetic discovery |
| `python3 -m project.scripts.run_fast_synthetic_certification` | Fast synthetic certification |
| `python3 -m project.scripts.validate_synthetic_detector_truth --run_id <id>` | Validate detector truth |
| `python3 -m project.scripts.generate_synthetic_crypto_regimes --suite_config ... --run_id ...` | Generate synthetic suite |
| `python3 -m project.scripts.run_golden_regression --run_id smoke_run` | Golden regression test |
| `python3 -m project.scripts.run_golden_workflow` | End-to-end golden workflow |
| `python3 -m project.scripts.run_benchmark_maintenance_cycle --execute 1` | Full benchmark cycle |
| `python3 -m project.scripts.show_benchmark_review --path <path>` | Display benchmark review |
| `python3 -m project.scripts.show_promotion_readiness --review <path> --cert <path>` | Display promotion readiness |
| `python3 project/scripts/spec_qa_linter.py` | Lint all YAML specs |

---

## Spec Validation CLI

```bash
python3 -m project.spec_validation.cli
```

Validates all YAML specs in `spec/` for structural correctness and cross-reference integrity. Run in Tier 1 CI.

---

## `ontology-consistency-audit`

```bash
ontology-consistency-audit --output docs/generated/ontology_audit.json --check
```

Checks that:

- All events in `spec/events/` have a matching family in `spec/grammar/family_registry.yaml`
- All templates used in events are legal for their family
- State specs are consistent with state registry
- Feature references in event specs match defined features

---

## Makefile Reference

Full target list (from `make help`):

```
discover-blueprints  Full research pipeline: Ingest → Discovery → Blueprints
discover-edges       Phase 2 discovery for all events
discover-target      Targeted: make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK
discover-concept     Concept-based: make discover-concept CONCEPT=<concept>
run                  Ingest + Clean + Features (preparation only)
baseline             Full discovery + profitable strategy packaging
golden-workflow      Canonical end-to-end smoke workflow
golden-certification Golden workflow + runtime certification manifest
test                 Full test suite
test-fast            Run fast research test profile
lint                 Ruff lint on changed Python files
format-check         Ruff formatter check
format               Ruff format in-place
style                lint + format-check
governance           Audit specs and sync schemas
benchmark-m0         Emit (or execute) frozen M0 benchmark run matrix
benchmark-maintenance-smoke  End-to-end dry-run of benchmark governance cycle
benchmark-maintenance Full production execution of benchmark governance cycle
clean-all-data       Wipe all data/lake and reports
minimum-green-gate   Required baseline: compile + architecture + spec + drift + golden
```

### Key Makefile Variables

```makefile
RUN_ID    ?= discovery_2020_2025
SYMBOLS   ?= BTCUSDT,ETHUSDT
START     ?= 2020-06-01
END       ?= 2025-07-10
TIMEFRAMES ?= 5m
EVENT     =              # required for discover-target
CONCEPT   =              # required for discover-concept
```
