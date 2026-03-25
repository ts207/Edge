# System Map

Generated from stage and artifact contract registries.

## Canonical Entrypoints

| Name | Kind | Module | Status | Description |
| --- | --- | --- | --- | --- |
| run_all_cli | orchestration_entrypoint | `project.pipelines.run_all` | canonical | Primary orchestration CLI entrypoint. |
| candidate_discovery_service | service | `project.research.services.candidate_discovery_service` | canonical | Canonical phase-2 discovery service. |
| promotion_service | service | `project.research.services.promotion_service` | canonical | Canonical promotion service. |
| reporting_service | service | `project.research.services.reporting_service` | canonical | Schema-aware reporting service for discovery and promotion outputs. |

## Compatibility Surfaces

Legacy wrapper surfaces have been removed.


## Stage Families

### `ingest`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `ingest_binance_um_ohlcv_*`, `ingest_binance_um_funding`, `ingest_binance_spot_ohlcv_*`, `ingest_binance_um_liquidation_snapshot`, `ingest_binance_um_open_interest_hist`
- Script patterns: `pipelines/ingest/ingest_binance_um_ohlcv*.py`, `pipelines/ingest/ingest_binance_um_funding.py`, `pipelines/ingest/ingest_binance_spot_ohlcv*.py`, `pipelines/ingest/ingest_binance_um_liquidation_snapshot.py`, `pipelines/ingest/ingest_binance_um_open_interest_hist.py`

### `core`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `build_cleaned_*`, `build_features*`, `build_universe_snapshots`, `build_context_features*`, `build_market_context*`, `build_microstructure_rollup*`, `validate_feature_integrity*`, `validate_data_coverage*`, `validate_context_entropy`
- Script patterns: `pipelines/clean/build_cleaned_bars.py`, `pipelines/features/build_features.py`, `pipelines/ingest/build_universe_snapshots.py`, `pipelines/features/build_context_features.py`, `pipelines/features/build_market_context.py`, `pipelines/features/build_microstructure_rollup.py`, `pipelines/clean/validate_feature_integrity.py`, `pipelines/clean/validate_data_coverage.py`, `pipelines/clean/validate_context_entropy.py`

### `runtime_invariants`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `build_normalized_replay_stream`, `run_causal_lane_ticks`, `run_determinism_replay_checks`, `run_oms_replay_validation`
- Script patterns: `pipelines/runtime/build_normalized_replay_stream.py`, `pipelines/runtime/run_causal_lane_ticks.py`, `pipelines/runtime/run_determinism_replay_checks.py`, `pipelines/runtime/run_oms_replay_validation.py`

### `phase1_analysis`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `analyze_*`, `phase1_correlation_clustering`
- Script patterns: `pipelines/research/analyze_*.py`, `pipelines/research/phase1_correlation_clustering.py`

### `phase2_event_registry`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `build_event_registry*`, `canonicalize_event_episodes*`
- Script patterns: `pipelines/research/build_event_registry.py`, `pipelines/research/canonicalize_event_episodes.py`

### `phase2_discovery`

- Owner service: `project.research.services.candidate_discovery_service`
- Stage patterns: `phase2_conditional_hypotheses*`, `bridge_evaluate_phase2*`, `summarize_discovery_quality`, `phase2_search_engine`, `finalize_experiment`
- Script patterns: `pipelines/research/phase2_candidate_discovery.py`, `pipelines/research/bridge_evaluate_phase2.py`, `pipelines/research/summarize_discovery_quality.py`, `pipelines/research/phase2_search_engine.py`, `pipelines/research/finalize_experiment.py`

### `promotion`

- Owner service: `project.research.services.promotion_service`
- Stage patterns: `evaluate_naive_entry`, `generate_negative_control_summary`, `promote_candidates`, `update_edge_registry`, `update_campaign_memory`, `export_edge_candidates`
- Script patterns: `pipelines/research/evaluate_naive_entry.py`, `pipelines/research/generate_negative_control_summary.py`, `pipelines/research/promote_candidates.py`, `pipelines/research/update_edge_registry.py`, `pipelines/research/update_campaign_memory.py`, `pipelines/research/export_edge_candidates.py`

### `research_quality`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `analyze_conditional_expectancy`, `validate_expectancy_traps`, `generate_recommendations_checklist`
- Script patterns: `pipelines/research/analyze_conditional_expectancy.py`, `pipelines/research/validate_expectancy_traps.py`, `pipelines/research/generate_recommendations_checklist.py`

### `strategy_packaging`

- Owner service: `project.pipelines.run_all`
- Stage patterns: `compile_strategy_blueprints`, `build_strategy_candidates`, `select_profitable_strategies`
- Script patterns: `pipelines/research/compile_strategy_blueprints.py`, `pipelines/research/build_strategy_candidates.py`, `pipelines/research/select_profitable_strategies.py`

## Artifact Contracts

### `ingest_binance_um_funding`

- Inputs: _none_
- Optional inputs: _none_
- Outputs: `raw.perp.funding_5m`
- External inputs: _none_

### `ingest_binance_um_liquidation_snapshot`

- Inputs: _none_
- Optional inputs: _none_
- Outputs: `raw.perp.liquidations`
- External inputs: _none_

### `ingest_binance_um_open_interest_hist`

- Inputs: _none_
- Optional inputs: _none_
- Outputs: `raw.perp.open_interest`
- External inputs: _none_

### `ingest_binance_um_ohlcv_{tf}`

- Inputs: _none_
- Optional inputs: _none_
- Outputs: `raw.perp.ohlcv_{tf}`
- External inputs: _none_

### `ingest_binance_spot_ohlcv_{tf}`

- Inputs: _none_
- Optional inputs: _none_
- Outputs: `raw.spot.ohlcv_{tf}`
- External inputs: _none_

### `build_cleaned_{tf}`

- Inputs: `raw.perp.ohlcv_{tf}`
- Optional inputs: _none_
- Outputs: `clean.perp.*`
- External inputs: `raw.perp.ohlcv_{tf}`

### `build_cleaned_{tf}_spot`

- Inputs: `raw.spot.ohlcv_{tf}`
- Optional inputs: _none_
- Outputs: `clean.spot.*`
- External inputs: `raw.spot.ohlcv_{tf}`

### `build_features_{tf}`

- Inputs: `clean.perp.*`
- Optional inputs: `raw.perp.funding_{tf}`, `raw.perp.liquidations`, `raw.perp.open_interest`
- Outputs: `features.perp.v2`
- External inputs: `clean.perp.*`, `raw.perp.funding_{tf}`, `raw.perp.liquidations`, `raw.perp.open_interest`

### `build_features_{tf}_spot`

- Inputs: `clean.spot.*`
- Optional inputs: _none_
- Outputs: `features.spot.v2`
- External inputs: `clean.spot.*`

### `build_universe_snapshots`

- Inputs: `clean.perp.*`
- Optional inputs: _none_
- Outputs: `metadata.universe_snapshots`
- External inputs: `clean.perp.*`

### `build_context_features*`

- Inputs: `features.perp.v2`
- Optional inputs: _none_
- Outputs: `context.features`
- External inputs: `features.perp.v2`

### `build_market_context*`

- Inputs: `features.perp.v2`
- Optional inputs: _none_
- Outputs: `context.market_state`
- External inputs: `features.perp.v2`

### `build_microstructure_rollup*`

- Inputs: `features.perp.v2`
- Optional inputs: _none_
- Outputs: `context.microstructure`
- External inputs: `features.perp.v2`

### `validate_feature_integrity*`

- Inputs: `features.perp.v2`
- Optional inputs: _none_
- Outputs: _none_
- External inputs: _none_

### `validate_data_coverage*`

- Inputs: `clean.perp.*`
- Optional inputs: _none_
- Outputs: _none_
- External inputs: _none_

### `validate_context_entropy`

- Inputs: `context.features`
- Optional inputs: _none_
- Outputs: _none_
- External inputs: _none_

### `build_normalized_replay_stream`

- Inputs: `metadata.universe_snapshots`
- Optional inputs: _none_
- Outputs: `runtime.normalized_stream`
- External inputs: _none_

### `run_causal_lane_ticks`

- Inputs: `runtime.normalized_stream`
- Optional inputs: _none_
- Outputs: `runtime.causal_ticks`
- External inputs: _none_

### `run_determinism_replay_checks`

- Inputs: `runtime.causal_ticks`
- Optional inputs: _none_
- Outputs: `runtime.determinism_checks`
- External inputs: _none_

### `run_oms_replay_validation`

- Inputs: `runtime.causal_ticks`
- Optional inputs: _none_
- Outputs: `runtime.oms_replay`
- External inputs: _none_

### `analyze_*`

- Inputs: _none_
- Optional inputs: `features.perp.v2`, `context.market_state`, `context.microstructure`
- Outputs: `phase1.events.{event_type}`
- External inputs: `features.perp.v2`, `context.market_state`, `context.microstructure`

### `phase1_correlation_clustering`

- Inputs: _none_
- Optional inputs: `phase1.events.*`
- Outputs: `phase1.correlation_clustering`
- External inputs: _none_

### `build_event_registry*`

- Inputs: _none_
- Optional inputs: `phase1.events.*`
- Outputs: `phase2.event_registry.{event_type}`
- External inputs: `phase1.events.*`

### `canonicalize_event_episodes*`

- Inputs: `phase2.event_registry.{event_type}`
- Optional inputs: _none_
- Outputs: `phase2.event_episodes.{event_type}`
- External inputs: `phase2.event_registry.{event_type}`

### `phase2_conditional_hypotheses*`

- Inputs: `phase2.event_episodes.{event_type}`, `features.perp.v2`
- Optional inputs: `context.market_state`, `context.microstructure`
- Outputs: `phase2.candidates.{event_type}`
- External inputs: `phase2.event_episodes.{event_type}`, `features.perp.v2`, `context.market_state`, `context.microstructure`

### `bridge_evaluate_phase2*`

- Inputs: `phase2.candidates.{event_type}`
- Optional inputs: _none_
- Outputs: `phase2.bridge_metrics.{event_type}`, `phase2.bridge_summary.{event_type}`, `phase2.bridge_enriched_candidates.{event_type}`
- External inputs: `phase2.candidates.{event_type}`

### `phase2_search_engine`

- Inputs: `features.perp.v2`
- Optional inputs: _none_
- Outputs: `phase2.candidates.search`
- External inputs: `features.perp.v2`

### `finalize_experiment`

- Inputs: _none_
- Optional inputs: `phase2.candidates.*`
- Outputs: `experiment.tested_ledger`
- External inputs: _none_

### `summarize_discovery_quality`

- Inputs: `phase2.candidates.*`
- Optional inputs: `phase2.bridge_summary.*`
- Outputs: `phase2.discovery_quality_summary`
- External inputs: _none_

### `evaluate_naive_entry`

- Inputs: `phase2.candidates.*`
- Optional inputs: _none_
- Outputs: `phase2.naive_entry_eval`
- External inputs: _none_

### `export_edge_candidates`

- Inputs: `phase2.candidates.*`
- Optional inputs: `phase2.bridge_metrics.*`
- Outputs: `edge_candidates.normalized`
- External inputs: `phase2.candidates.*`, `phase2.bridge_metrics.*`

### `generate_negative_control_summary`

- Inputs: `edge_candidates.normalized`
- Optional inputs: _none_
- Outputs: `research.negative_control_summary`
- External inputs: `edge_candidates.normalized`

### `promote_candidates`

- Inputs: `edge_candidates.normalized`, `research.negative_control_summary`
- Optional inputs: `phase2.bridge_metrics.*`, `phase2.naive_entry_eval`
- Outputs: `promotion.audit`, `promotion.promoted_candidates`
- External inputs: `edge_candidates.normalized`, `research.negative_control_summary`, `phase2.bridge_metrics.*`, `phase2.naive_entry_eval`

### `update_edge_registry`

- Inputs: `promotion.audit`, `promotion.promoted_candidates`
- Optional inputs: _none_
- Outputs: `history.candidate.edge_observations`, `history.candidate.edge_registry`, `edge_registry.snapshot`
- External inputs: `promotion.audit`, `promotion.promoted_candidates`

### `update_campaign_memory`

- Inputs: _none_
- Optional inputs: `edge_candidates.normalized`, `promotion.audit`, `history.candidate.edge_registry`, `phase2.discovery_quality_summary`
- Outputs: `experiment.memory.tested_regions`, `experiment.memory.reflections`, `experiment.memory.failures`
- External inputs: `edge_candidates.normalized`, `promotion.audit`, `history.candidate.edge_registry`, `phase2.discovery_quality_summary`

### `analyze_conditional_expectancy`

- Inputs: `history.candidate.edge_registry`
- Optional inputs: _none_
- Outputs: `research.expectancy_analysis`
- External inputs: `history.candidate.edge_registry`

### `validate_expectancy_traps`

- Inputs: `research.expectancy_analysis`
- Optional inputs: _none_
- Outputs: `research.expectancy_traps`
- External inputs: _none_

### `generate_recommendations_checklist`

- Inputs: `research.expectancy_traps`
- Optional inputs: _none_
- Outputs: `research.recommendations_checklist`
- External inputs: _none_

### `compile_strategy_blueprints`

- Inputs: `research.recommendations_checklist`
- Optional inputs: _none_
- Outputs: `strategy.blueprints`
- External inputs: _none_

### `build_strategy_candidates`

- Inputs: `strategy.blueprints`
- Optional inputs: _none_
- Outputs: `strategy.candidates`
- External inputs: _none_

### `select_profitable_strategies`

- Inputs: _none_
- Optional inputs: `strategy.candidates`
- Outputs: `strategy.profitable`
- External inputs: `strategy.candidates`
