# Edge

A research platform for event-driven alpha discovery in crypto markets.

Edge turns market observations into explicit, testable hypotheses, runs them through a structured pipeline, and gates any result on mechanical, statistical, and deployment-readiness checks before it can be promoted. The goal is reproducible, cost-aware, narrowly attributed research — not output volume.

---

## What It Does

The pipeline runs in eight stages:

```
ingest → clean → build_features → build_market_context
  → phase1_analysis (detect events)
  → phase2_discovery (evaluate hypotheses)
  → promotion (gate candidates)
  → strategy_packaging (compile blueprints)
```

Each stage produces versioned, manifest-tracked artifacts. A run is only trustworthy when its artifacts reconcile — a `0` exit code is not sufficient.

---

## Install

**Requires Python 3.11+**

```bash
pip install -e .
```

---

## Quickstart

Plan a run before executing it:

```bash
edge-run-all \
  --run_id demo \
  --symbols BTCUSDT \
  --start 2024-01-01 \
  --end 2024-03-31 \
  --plan_only 1
```

Remove `--plan_only 1` to execute. Always plan first on material runs.

---

## Common Commands

### Pipeline

```bash
# Full pipeline (plan first)
edge-run-all --run_id <id> --symbols BTCUSDT --start 2024-01-01 --end 2024-03-31 --plan_only 1

# Phase 2 discovery only
edge-phase2-discovery --run_id <id>

# Promotion pass
edge-promote --run_id <id>
```

### Research

```bash
# Broad edge discovery
make discover-edges

# Targeted event discovery
make discover-target SYMBOLS=BTCUSDT EVENT=VOL_SHOCK

# Inspect knowledge base and prior memory
python3 -m project.research.knowledge.query knobs
python3 -m project.research.knowledge.query memory --program_id btc_campaign
python3 -m project.research.knowledge.query static --event BASIS_DISLOC
```

### Synthetic Validation

```bash
# Broad synthetic discovery (maintained golden workflow)
python3 -m project.scripts.run_golden_synthetic_discovery

# Fast certification (narrow, for CI/pre-merge)
python3 -m project.scripts.run_fast_synthetic_certification

# Validate detector truth after any synthetic run
python3 -m project.scripts.validate_synthetic_detector_truth --run_id golden_synthetic_discovery
```

### Benchmarks

```bash
# Run full maintenance cycle and certify
make benchmark-maintenance

# Review latest certified results
PYTHONPATH=. python3 project/scripts/show_benchmark_review.py
```

### Live Engine

```bash
# Inspect session metadata
edge-live-engine --config project/configs/golden_certification.yaml --print_session_metadata

# Launch with state snapshot
edge-live-engine --config project/configs/golden_certification.yaml --snapshot_path artifacts/live_state.json
```

Systemd service templates: `deploy/systemd/`. Environment templates: `deploy/env/`.

### Build and Test

```bash
make test           # Full test suite under project/tests
make test-fast      # Excludes @pytest.mark.slow
make lint           # Ruff lint
make format-check   # Ruff format check (no writes)
make format         # Apply formatting
```

### Maintenance

```bash
# Regenerate machine-owned architecture artifacts
python3 -m project.scripts.build_system_map --check
python3 -m project.scripts.detector_coverage_audit \
  --md-out docs/generated/detector_coverage.md \
  --json-out docs/generated/detector_coverage.json \
  --check
```

Generated inventories and metrics live in `docs/generated/`. Treat those artifacts as the source of truth for current detector coverage, ontology status, and architecture metrics.

---

## Repo Layout

```
project/           Application code
  pipelines/       Stage entrypoints and orchestration
  events/          Detectors, families, registries
  features/        Shared feature and regime helpers
  research/        Discovery, promotion, evaluation, diagnostics
  strategy/        DSL, templates, runtime
  contracts/       Stage and artifact contracts
  spec_registry/   YAML spec loaders
  live/            Live engine and kill-switch
  scripts/         Operator and maintenance entry points
  tests/           Regression, contract, smoke, and architecture tests

spec/              YAML definitions: events, features, states, grammar, search, strategies
docs/              Operator and reference documentation
  researcher/      Research operator docs (loop, experiments, guardrails, ontology)
  developer/       Developer docs (architecture, maintenance, tech stack)
  generated/       Machine-owned diagnostics — do not hand-edit
deploy/            Systemd units and environment templates
data/              Local runtime outputs (not source files)
```

---

## Key Surfaces

| Surface | Path |
|---|---|
| End-to-end orchestrator | `project/pipelines/run_all.py` |
| Stage and artifact contracts | `project/contracts/pipeline_registry.py` |
| Discovery service | `project/research/services/candidate_discovery_service.py` |
| Promotion service | `project/research/services/promotion_service.py` |
| Detector catalog | `project/events/detectors/catalog.py` |
| Strategy DSL | `project/strategy/dsl/` |
| Strategy templates | `project/strategy/templates/` |
| Feature registry | `project/core/feature_registry.py` |
| Agent I/O (proposal → run) | `project/research/agent_io/` |

---

## The Research Unit

The platform is built around **hypotheses**, not detectors and not strategies.

A hypothesis specifies an event, a canonical family, a template, a context, a side, a horizon, an entry lag, and a symbol scope. That is what gets evaluated, stored in memory, and gated in promotion.

The 9 canonical event families (`LIQUIDITY_DISLOCATION`, `VOLATILITY_TRANSITION`, `POSITIONING_EXTREMES`, `FORCED_FLOW_AND_EXHAUSTION`, `TREND_STRUCTURE`, `STATISTICAL_DISLOCATION`, `REGIME_TRANSITION`, `INFORMATION_DESYNC`, `TEMPORAL_STRUCTURE`) constrain which templates are legal for each event type.

---

## Agent / Autonomous Controller Quickstart

```bash
# 1. Inspect knobs and prior memory
python3 -m project.research.knowledge.query knobs
python3 -m project.research.knowledge.query memory --program_id btc_campaign

# 2. Translate a proposal YAML to repo-native config
python3 -m project.research.agent_io.proposal_to_experiment \
  --proposal /path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --config_path /tmp/experiment.yaml \
  --overrides_path /tmp/run_all_overrides.json

# 3. Plan before running
python3 -m project.research.agent_io.issue_proposal \
  --proposal /path/to/proposal.yaml \
  --registry_root project/configs/registries \
  --plan_only 1
```

The full operator guide for autonomous controllers is in [`CLAUDE.md`](CLAUDE.md).

---

## Core Rules

- **Artifacts are the source of truth.** Read manifests before interpreting output.
- **`plan_only` before material runs.** Verify scope before execution.
- **Synthetic runs are calibration, not proof.** Do not present synthetic profitability as live-market evidence.
- **Promotion is a gate.** Attractive discovery output is not promotion readiness.
- **Narrow before broad.** One family, one template, one context per run by default.
