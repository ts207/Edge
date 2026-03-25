# Edge — Architecture Reference

## Pipeline Stages

The full pipeline runs in 8 ordered stages. Each stage produces versioned, manifest-tracked artifacts.

```
ingest → clean → build_features → build_market_context
  → phase1_analysis (detect events)
  → phase2_discovery (evaluate hypotheses)
  → promotion (gate candidates)
  → strategy_packaging (compile blueprints)
```

### Stage Family Contracts

| Stage Family | Owner Module | Stage Patterns |
|---|---|---|
| `ingest` | `project.pipelines.run_all` | `ingest_binance_um_ohlcv_*`, `ingest_binance_um_funding`, `ingest_binance_spot_ohlcv_*`, `ingest_binance_um_liquidation_snapshot`, `ingest_binance_um_open_interest_hist` |
| `core` | `project.pipelines.run_all` | `build_cleaned_*`, `build_features*`, `build_universe_snapshots`, `build_context_features*`, `build_market_context*`, `build_microstructure_rollup*`, `validate_*` |
| `runtime_invariants` | `project.pipelines.run_all` | `build_normalized_replay_stream`, `run_causal_lane_ticks`, `run_determinism_replay_checks`, `run_oms_replay_validation` |
| `phase1_analysis` | `project.pipelines.run_all` | `analyze_*`, `phase1_correlation_clustering` |
| `phase2_event_registry` | `project.pipelines.run_all` | `build_event_registry*`, `canonicalize_event_episodes*` |
| `phase2_discovery` | `project.research.services.candidate_discovery_service` | `phase2_conditional_hypotheses*`, `bridge_evaluate_phase2*`, `summarize_discovery_quality`, `phase2_search_engine`, `finalize_experiment` |
| `promotion` | `project.research.services.promotion_service` | `evaluate_naive_entry`, `generate_negative_control_summary`, `promote_candidates`, `update_edge_registry`, `update_campaign_memory`, `export_edge_candidates` |
| `research_quality` | `project.pipelines.run_all` | `analyze_conditional_expectancy`, `validate_expectancy_traps`, `generate_recommendations_checklist` |
| `strategy_packaging` | `project.pipelines.run_all` | `compile_strategy_blueprints`, `build_strategy_candidates`, `select_profitable_strategies` |

---

## Artifact Flow (Data Contracts)

Each stage declares its input and output artifact tokens. Tokens are canonical strings like `raw.perp.ohlcv_5m`.

| Stage | Inputs | Outputs |
|---|---|---|
| `ingest_binance_um_funding` | — | `raw.perp.funding_5m` |
| `ingest_binance_um_liquidation_snapshot` | — | `raw.perp.liquidations` |
| `ingest_binance_um_open_interest_hist` | — | `raw.perp.open_interest` |
| `ingest_binance_um_ohlcv_{tf}` | — | `raw.perp.ohlcv_{tf}` |
| `ingest_binance_spot_ohlcv_{tf}` | — | `raw.spot.ohlcv_{tf}` |
| `build_cleaned_{tf}` | `raw.perp.ohlcv_{tf}` | `clean.perp.*` |
| `build_cleaned_{tf}_spot` | `raw.spot.ohlcv_{tf}` | `clean.spot.*` |
| `build_features_{tf}` | `clean.perp.*` + optional funding/liq/OI | `features.perp.v2` |
| `build_features_{tf}_spot` | `clean.spot.*` | `features.spot.v2` |
| `build_universe_snapshots` | `clean.perp.*` | `metadata.universe_snapshots` |

---

## Canonical Entrypoints

| Name | Kind | Module |
|---|---|---|
| `run_all_cli` | orchestration_entrypoint | `project.pipelines.run_all` |
| `candidate_discovery_service` | service | `project.research.services.candidate_discovery_service` |
| `promotion_service` | service | `project.research.services.promotion_service` |
| `reporting_service` | service | `project.research.services.reporting_service` |

---

## Package Topology

### Top-Level Packages

```
project/
├── apps/          Pipeline app manifests
├── artifacts/     Baseline artifact snapshots (frozen reference state)
├── compilers/     Strategy compiler (backtest → live translation)
├── configs/       Runtime configs, experiment registries, venue configs
├── contracts/     Stage and artifact contracts (pipeline_registry.py)
├── core/          Shared infrastructure: feature registry, config, timeframes, exceptions
├── domain/        Domain models (promotion)
├── engine/        Backtest execution engine
├── eval/          Evaluation utilities
├── events/        Event detectors, family modules, registries, adapters
├── execution/     Backtest and runtime execution
├── experiments/   Experiment config loader and schema
├── features/      Feature builders and shared regime helpers
├── infra/         IO and orchestration infrastructure
├── io/            File I/O utilities
├── live/          Live engine, WebSocket ingestion, kill-switch
├── pipelines/     Stage entrypoints and orchestration (main pipeline logic)
├── portfolio/     Portfolio-level aggregation
├── reliability/   Smoke tests and reliability CLI
├── research/      Discovery, promotion, evaluation, knowledge, agent I/O
├── schemas/       Shared Pydantic/Pandera schemas
├── scripts/       Operator and maintenance entry points
├── spec_registry/ YAML spec loaders
├── spec_validation/ Spec linting and consistency checks
├── specs/         Manifest utilities
├── strategy/      Strategy DSL, templates, runtime, compiler
└── tests/         All test suites
```

### Critical Cross-Package Dependencies

```
pipelines.run_all
  ↳ contracts.pipeline_registry     (stage/artifact contracts)
  ↳ pipelines.pipeline_planning     (argument parsing, preflight)
  ↳ pipelines.pipeline_execution    (stage runner)
  ↳ pipelines.pipeline_provenance   (manifest, lineage, fingerprint)
  ↳ events.event_specs              (EVENT_REGISTRY_SPECS)
  ↳ events.phase2                   (PHASE2_EVENT_CHAIN)
  ↳ research.services.*             (discovery, promotion, reporting)

research.services.candidate_discovery_service
  ↳ research.phase2                 (load_features, prepare_events_dataframe)
  ↳ research.gating                 (build_event_return_frame)
  ↳ research.hypothesis_registry    (Hypothesis, HypothesisRegistry)
  ↳ research.validation             (estimate_effect_from_frame)
  ↳ events.event_specs              (EVENT_REGISTRY_SPECS)

strategy.dsl
  ↳ strategy.dsl.schema             (Blueprint, EntrySpec, ExitSpec, ...)
  ↳ strategy.dsl.contract_v1        (validation, normalization)
  ↳ strategy.dsl.policies           (DEFAULT_POLICY, EVENT_POLICIES)
  ↳ strategy.dsl.references         (REGISTRY_SIGNAL_COLUMNS)
```

---

## Live Engine Architecture

The live engine subscribes to Binance WebSocket streams and replicates the research pipeline in real time.

```
Binance WebSocket (kline_1m, kline_5m, bookTicker)
    │
    ▼
LiveDataManager (project.live.ingest.manager)
    │  kline_queue + ticker_queue (asyncio.Queue, maxsize=10000)
    ▼
BinanceWebSocketClient (project.live.ingest.ws_client)
    │  reconnect-resilient, health monitor
    ▼
Live Feature Computation
    ▼
Event Detection (same detectors as research pipeline)
    ▼
Strategy DSL Runtime (project.strategy.runtime.dsl_runtime)
    ▼
Order Management (OMS, causal lane enforcement)
    ▼
Kill Switch (project.live.kill_switch, project.spec/grammar/kill_switch_config.yaml)
```

**WebSocket streams per symbol:**

- `{symbol}@kline_1m`
- `{symbol}@kline_5m`
- `{symbol}@bookTicker`

**Deployment:** Systemd service unit at `deploy/systemd/edge-live-engine.service`. Runs as `edge-live-engine --config project/configs/golden_certification.yaml --snapshot_path /var/lib/edge/live_state.json`.

---

## Event Detector Architecture

Detectors are organized by family module and loaded dynamically via a catalog.

```
project/events/
├── detectors/
│   ├── catalog.py           → load_detector_family_modules() — dynamic importer
│   └── extended_detectors.py
├── families/
│   ├── basis.py
│   ├── funding.py
│   ├── liquidation.py
│   ├── liquidity.py
│   ├── oi.py
│   ├── canonical_proxy.py
│   ├── volatility.py
│   ├── regime.py
│   ├── temporal.py
│   ├── desync.py
│   ├── trend.py
│   ├── statistical.py
│   └── exhaustion.py
├── registries/              → event type → detector mapping
├── adapters/                → format adapters for detector output
├── event_specs.py           → EVENT_REGISTRY_SPECS (global registry)
└── phase2.py                → PHASE2_EVENT_CHAIN, load_features
```

Each family module registers its detectors at import time. `load_detector_family_modules()` triggers all registrations.

---

## Strategy DSL Architecture

Strategies are expressed as declarative **Blueprints** with typed components.

```
Blueprint
├── LineageSpec      (event → family → template → hypothesis linkage)
├── EntrySpec        (trigger, lag, conditions)
├── ExitSpec         (stop, target, time-exit)
├── SizingSpec       (position sizing rules)
├── ExecutionSpec    (slippage model, cost assumptions)
├── EvaluationSpec   (horizon, lookforward bars)
├── OverlaySpec[]    (regime filters, context gates)
└── SymbolScopeSpec  (which instruments)
```

Blueprints are compiled to executable strategy specs via `project/strategy/compiler/`.

---

## CI/CD Tier Structure

| Tier | Trigger | What It Checks |
|---|---|---|
| **Tier 1** — Structural Fast Gate | push/PR to main | Compile check, architecture tests, spec validation, ontology/detector/system-map drift, fast regression tests, Pyright static typing |
| **Tier 2** | Scheduled or manual | Broader test suite, extended regression, benchmark smoke |
| **Tier 3** | Manual / release | Full test suite including slow tests, golden workflow certification |

Automated agent workflows (via GitHub Actions): Codex PR review, Gemini triage/invoke/scheduled-triage/review.

---

## Artifact and Manifest System

Every run produces a **manifest** that must reconcile for the run to be trusted.

**Read order for artifact trust:**

1. Top-level run manifest
2. Stage manifests
3. Stage logs
4. Report artifacts
5. Generated diagnostics (in `docs/generated/`)

**Machine-owned artifacts** (do not hand-edit):

- `docs/generated/architecture_metrics.json`
- `docs/generated/detector_coverage.json` + `.md`
- `docs/generated/ontology_audit.json`
- `docs/generated/system_map.json` + `.md`

These are regenerated by maintenance scripts and checked for drift in CI.
