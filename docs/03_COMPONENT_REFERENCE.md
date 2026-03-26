# Edge — Component Reference

## Pipelines Layer (`project/pipelines/`)

### Orchestration

| Module | Role |
|---|---|
| `pipelines/run_all.py` | Primary end-to-end orchestrator CLI. Entry point: `edge-run-all`. Coordinates all 8 pipeline stage families. |
| `pipelines/run_all_bootstrap.py` | Bootstraps run state before stage execution begins |
| `pipelines/run_all_finalize.py` | Post-run finalization: KPI scorecard, artifact summary, postflight audit |
| `pipelines/run_all_support.py` | Startup guard evaluation, flag utilities |
| `pipelines/run_all_provenance.py` | Phase2 event chain validation, data fingerprint computation |
| `pipelines/effective_config.py` | Builds and writes the effective config payload for a run |
| `pipelines/execution_engine.py` | Core stage execution logic |
| `pipelines/execution_manifest.py` | Manifest creation and management |
| `pipelines/execution_result.py` | Execution result types |
| `pipelines/pipeline_defaults.py` | DATA_ROOT, utc_now_iso, run_id_default, timing utilities |
| `pipelines/pipeline_planning.py` | Argument parsing (build_parser), preflight, stage instance IDs |
| `pipelines/pipeline_execution.py` | execute_pipeline_stages, seed/finalize manifest, run_stage |
| `pipelines/pipeline_provenance.py` | Data fingerprint, feature schema metadata, git commit, manifest I/O |
| `pipelines/pipeline_audit.py` | Terminal audit, runtime postflight, failure message emission |
| `pipelines/pipeline_summary.py` | KPI scorecard writing, artifact summary printing |
| `pipelines/stage_registry.py` | Stage registration and lookup |
| `pipelines/stage_definitions.py` | Re-exports all contracts from `project.contracts.pipeline_registry` |
| `pipelines/stage_dependencies.py` | Stage dependency graph |
| `pipelines/stage_defaults.py` | Default stage parameters |
| `pipelines/planner.py` | Run planning utilities |
| `pipelines/spec.py` | Pipeline spec helpers |

### Ingest Stage (`pipelines/ingest/`)

| Module | Artifact Output |
|---|---|
| `ingest_binance_um_ohlcv.py` | `raw.perp.ohlcv_{tf}` (perpetual OHLCV) |
| `ingest_binance_spot_ohlcv_1m.py` | `raw.spot.ohlcv_1m` |
| `ingest_binance_spot_ohlcv_5m.py` | `raw.spot.ohlcv_5m` |
| `ingest_binance_um_funding.py` | `raw.perp.funding_5m` |
| `ingest_binance_um_mark_price_1m.py` | Mark price (1m) |
| `ingest_binance_um_mark_price_5m.py` | Mark price (5m) |
| `ingest_binance_um_book_ticker.py` | Top-of-book ticker |
| `ingest_binance_um_open_interest_hist.py` | `raw.perp.open_interest` |
| `ingest_binance_um_liquidation_snapshot.py` | `raw.perp.liquidations` |
| `build_universe_snapshots.py` | `metadata.universe_snapshots` |
| `run_slice1_data_layer.py` | Slice 1 data layer orchestrator |

### Clean Stage (`pipelines/clean/`)

| Module | Role |
|---|---|
| `build_cleaned_bars.py` | Produces `clean.perp.*` and `clean.spot.*` from raw OHLCV |
| `build_basis_state_5m.py` | Computes spot-perp basis state at 5m |
| `build_tob_5m_agg.py` | Top-of-book 5m aggregation |
| `build_tob_snapshots_1s.py` | 1-second TOB snapshots |
| `calibrate_execution_costs.py` | Execution cost calibration from TOB data |
| `validate_data_coverage.py` | Validates temporal coverage completeness |
| `validate_feature_integrity.py` | Validates feature schema correctness |
| `validate_context_entropy.py` | Validates context feature entropy |

### Features Stage (`pipelines/features/`)

| Module | Role |
|---|---|
| `build_features.py` | Computes all registered features → `features.perp.v2` / `features.spot.v2` |
| `build_market_context.py` | Regime classification, context feature assembly |
| `build_microstructure_rollup.py` | Microstructure feature aggregation |

### Research Stages (`pipelines/research/`)

| Module | Role |
|---|---|
| `phase2_candidate_discovery.py` | Phase 2 hypothesis evaluation. Entry point: `edge-phase2-discovery` |
| `promote_candidates.py` | Promotion pass. Entry point: `edge-promote` |
| `compile_strategy_blueprints.py` | Blueprint compilation. Entry point: `compile-strategy-blueprints` |
| `build_strategy_candidates.py` | Strategy candidate assembly. Entry point: `build-strategy-candidates` |
| `cost_calibration.py` | Cost calibration within research pipeline |
| `direction_semantics.py` | Side/direction resolution |
| `holdout_integrity.py` | Train/validation/test split enforcement |
| `cli/candidate_discovery_cli.py` | CLI wrapper for discovery |
| `cli/promotion_cli.py` | CLI wrapper for promotion |

---

## Events Layer (`project/events/`)

### Detector Catalog

| Module | Role |
|---|---|
| `detectors/catalog.py` | `load_detector_family_modules()` — dynamically imports all family modules to register detectors |
| `detectors/extended_detectors.py` | Extended/composite detector implementations |
| `event_specs.py` | `EVENT_REGISTRY_SPECS` — global event type registry loaded from YAML |
| `phase2.py` | `PHASE2_EVENT_CHAIN`, `load_features`, `prepare_events_dataframe` |

### Family Modules (each registers its detectors at import)

| Module | Events It Covers |
|---|---|
| `families/basis.py` | Basis dislocation, spot-perp divergence events |
| `families/funding.py` | Funding rate extremes, flips, normalization, persistence |
| `families/liquidation.py` | Liquidation cascade, exhaustion reversal |
| `families/liquidity.py` | Depth collapse, liquidity gap, vacuum, absorption proxy |
| `families/oi.py` | OI spikes, flushes, positioning extremes |
| `families/canonical_proxy.py` | Canonical proxy replacement events |
| `families/volatility.py` | Vol shock, spike, cluster shift, regime shift |
| `families/regime.py` | Beta spike, correlation breakdown, regime transition |
| `families/temporal.py` | Session open/close, scheduled news windows, fee regime |
| `families/desync.py` | Cross-venue desync, lead-lag break, index divergence |
| `families/trend.py` | Breakout, pullback, momentum divergence, trend acceleration/exhaustion |
| `families/statistical.py` | Band break, z-score stretch, range compression |
| `families/exhaustion.py` | Flow exhaustion, forced flow, deleveraging |

---

## Research Layer (`project/research/`)

### Services

| Module | Role |
|---|---|
| `services/candidate_discovery_service.py` | Canonical Phase 2 discovery. Scores hypotheses, applies FDR control (q-value), post-cost gating |
| `services/promotion_service.py` | Promotion service. Applies confirmatory gates (P3 deployable/shadow tiers) |
| `services/reporting_service.py` | Schema-aware reporting for discovery and promotion outputs |
| `services/run_comparison_service.py` | Compares two runs and writes a diff report |
| `services/candidate_discovery_scoring.py` | Scoring functions, multiple-testing correction |
| `services/candidate_discovery_diagnostics.py` | Sample quality gates, false-discovery diagnostics |
| `services/phase2_diagnostics.py` | Split counts, event preparation diagnostics |
| `services/phase2_support.py` | Bar-duration utilities |
| `services/pathing.py` | Phase 2 output path resolution |

### Knowledge System

| Module | Role |
|---|---|
| `knowledge/query.py` | CLI entrypoint: `python3 -m project.research.knowledge.query` — inspects knobs, memory, static facts |
| `knowledge/` | Memory schema, reflection, knowledge retrieval |

### Agent I/O

| Module | Role |
|---|---|
| `agent_io/proposal_to_experiment.py` | Translates proposal YAML → repo-native experiment config |
| `agent_io/issue_proposal.py` | Issues a proposal with memory bookkeeping |
| `agent_io/execute_proposal.py` | Executes or plans a proposal |

### Research Utilities

| Module | Role |
|---|---|
| `research/phase2.py` | Feature loading, event frame preparation |
| `research/gating.py` | `build_event_return_frame` |
| `research/hypothesis_registry.py` | `Hypothesis`, `HypothesisRegistry` |
| `research/validation.py` | `estimate_effect_from_frame` |
| `research/discovery.py` | Core discovery logic |
| `research/analyzers/` | Per-event analysis modules |
| `research/candidates/` | Candidate data models |
| `research/clustering/` | Correlation clustering (phase 1) |
| `research/event_quality/` | Event quality metrics |
| `research/robustness/` | Robustness testing |
| `research/stats/` | Statistical utilities |
| `research/promotion/` | Promotion domain logic |
| `research/search/` | Search engine for hypothesis space |
| `research/recommendations/` | Recommendations checklist |
| `research/reports/` | Report generation |
| `research/helpers/` | Shared helpers |
| `research/shared/` | Shared data models |
| `research/validation/` | Expectancy trap validation |
| `research/configs/` | Research-specific configs |

---

## Strategy Layer (`project/strategy/`)

### DSL

| Module | Role |
|---|---|
| `dsl/__init__.py` | Canonical umbrella namespace |
| `dsl/schema.py` | `Blueprint`, `EntrySpec`, `ExitSpec`, `SizingSpec`, `ExecutionSpec`, `EvaluationSpec`, `OverlaySpec`, `SymbolScopeSpec`, `LineageSpec`, `ConditionNodeSpec` |
| `dsl/contract_v1.py` | Validation, normalization, `is_executable_action`, `resolve_trigger_column`, `validate_feature_references` |
| `dsl/normalize.py` | `build_blueprint` |
| `dsl/conditions.py` | `ConditionRegistry` |
| `dsl/policies.py` | `DEFAULT_POLICY`, `EVENT_POLICIES`, `event_policy`, `overlay_defaults` |
| `dsl/references.py` | `REGISTRY_SIGNAL_COLUMNS`, `event_direction_bias` |
| `dsl/validate.py` | `validate_overlay_columns` |

### Templates

| Path | Role |
|---|---|
| `strategy/templates/` | YAML-defined strategy templates per event family |

### Compiler

| Module | Role |
|---|---|
| `strategy/compiler/` | Blueprint → Executable strategy translation layer |
| `compilers/executable_strategy_spec.py` | Executable strategy spec data class |

### Runtime

| Module | Role |
|---|---|
| `strategy/runtime/` | Strategy runtime: signal evaluation, position management |
| `strategy/runtime/dsl_runtime/` | DSL-native runtime executor |

---

## Core Layer (`project/core/`)

| Module | Role |
|---|---|
| `feature_registry.py` | `FeatureDefinition`, `register_feature_definition`, `list_feature_definitions` — global feature catalog |
| `config.py` | `get_data_root` and global config utilities |
| `timeframes.py` | `DEFAULT_TIMEFRAME`, `SUPPORTED_TIMEFRAMES`, artifact token builders, `normalize_timeframe`, `parse_timeframes` |
| `exceptions.py` | `ContractViolationError` and other domain exceptions |
| `execution_costs.py` | `resolve_execution_costs` — cost model lookup |

---

## Contracts Layer (`project/contracts/`)

| Module | Role |
|---|---|
| `pipeline_registry.py` | All `StageArtifactContract`, `StageFamilyContract`, `ResolvedStageArtifactContract` definitions. The single source of truth for what each stage consumes and produces. |

---

## Live Engine (`project/live/`)

| Module | Role |
|---|---|
| `live/ingest/manager.py` | `LiveDataManager` — manages WebSocket streams, kline/ticker queues |
| `live/ingest/ws_client.py` | `BinanceWebSocketClient` — reconnect-resilient WebSocket client |
| `live/ingest/parsers.py` | `parse_book_ticker_event`, `parse_kline_event` |
| `live/kill_switch` | Kill-switch enforcement at runtime |

---

## Scripts Layer (`project/scripts/`)

| Script | Purpose |
|---|---|
| `build_system_map.py` | Regenerates `docs/generated/system_map.{json,md}` |
| `detector_coverage_audit.py` | Regenerates `docs/generated/detector_coverage.{json,md}` |
| `ontology_consistency_audit.py` | Regenerates `docs/generated/ontology_audit.json`. Entry: `ontology-consistency-audit` |
| `build_architecture_metrics.py` | Regenerates `docs/generated/architecture_metrics.json` |
| `run_golden_synthetic_discovery.py` | Maintained golden synthetic discovery workflow |
| `run_fast_synthetic_certification.py` | Fast CI synthetic certification |
| `validate_synthetic_detector_truth.py` | Truth validation after synthetic runs |
| `generate_synthetic_crypto_regimes.py` | Generates synthetic dataset suite |
| `run_golden_regression.py` | Golden regression test |
| `run_golden_workflow.py` | End-to-end golden workflow smoke |
| `run_live_engine.py` | Live engine launcher. Entry: `edge-live-engine` |
| `run_benchmark_maintenance_cycle.py` | Full benchmark governance cycle |
| `show_benchmark_review.py` | Display latest certified benchmark results |
| `show_promotion_readiness.py` | Display promotion readiness from review + cert |
| `spec_qa_linter.py` | QA lint on all YAML specs |
| `clean_data.sh` | Wipes runtime data |
| `baseline/` | Baseline snapshot scripts |
| `debug/` | Debug utilities |
| `regression/` | Regression test scripts |

---

## Spec Registry (`project/spec_registry/`)

Loads YAML definitions from `spec/` into Python objects at startup. Key registries:

- Event spec registry (loads `spec/events/*.yaml`)
- Feature spec registry (loads `spec/features/*.yaml` / `spec/ontology/features/*.yaml`)
- State registry (loads `spec/states/*.yaml` / `spec/ontology/states/*.yaml`)
- Grammar registry (loads `spec/grammar/*.yaml`)
- Search space registry (loads `spec/search/*.yaml`)
- Template registry (loads `spec/templates/*.yaml`)

---

## Reliability (`project/reliability/`)

| Module | Role |
|---|---|
| `cli_smoke.py` | Smoke test CLI. Entry: `edge-smoke` |

---

## Test Suite Structure (`project/tests/`)

| Directory | What It Tests |
|---|---|
| `tests/architecture/` | Import structure, surface boundaries, no forbidden cross-package imports |
| `tests/contracts/` | Stage artifact schemas, manifest integrity, cross-artifact reconciliation, strategy trace schema, portfolio ledger schema |
| `tests/regressions/` | Named regression cases: position contracts, entry accounting, event analyzer market requirement, timeframe contracts, storage fallback, bundle policy |
| `tests/events/` | Event detector unit tests |
| `tests/features/` | Feature builder tests |
| `tests/research/` | Discovery, promotion, robustness, knowledge, agent I/O |
| `tests/strategy/` | DSL, blueprint, template tests |
| `tests/pipelines/` | Per-stage pipeline tests |
| `tests/live/` | Live engine tests |
| `tests/audit/` | Ontology and spec audit tests |
| `tests/smoke/` | End-to-end smoke tests |
| `tests/artifacts/` | Artifact integrity tests |
| `tests/replays/` | OMS and causal lane replay tests |
| `tests/pit/` | Point-in-time correctness tests |
| `tests/unit/` | General unit tests |

---

## Synthetic Truth Tools (`project/synthetic_truth/tools/`)

Utility package for synthetic market data generation and ground-truth validation.

| Module | Role |
|---|---|
| `tools/metrics/signal_quality.py` | Statistical signal quality metrics |
| `tools/scoring/normalize.py` | Signal score normalization |
| `tools/scoring/aggregate.py` | Weighted signal aggregation |
| `tools/temporal/event_chain.py` | Sequential event chain state machine |
| `tools/validation/conflicts.py` | Mutually exclusive event conflict detection |

