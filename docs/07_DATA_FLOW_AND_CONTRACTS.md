# Edge — Data Flow & Contracts

## Artifact Token System

Every pipeline stage declares its inputs and outputs as **artifact tokens** — canonical string identifiers. This is the contract layer between stages.

### Token Naming Convention

```
{tier}.{market}.{type}_{timeframe}
```

| Tier | Examples |
|---|---|
| `raw` | `raw.perp.ohlcv_5m`, `raw.perp.funding_5m`, `raw.perp.liquidations` |
| `clean` | `clean.perp.*`, `clean.spot.*` |
| `features` | `features.perp.v2`, `features.spot.v2` |
| `metadata` | `metadata.universe_snapshots` |

Tokens are assembled by factory functions in `project.core.timeframes`:

```python
make_ohlcv_artifact_token(timeframe)       # → "raw.perp.ohlcv_{tf}"
make_spot_ohlcv_artifact_token(timeframe)  # → "raw.spot.ohlcv_{tf}"
make_clean_artifact_token(timeframe, market) # → "clean.{market}.*"
make_feature_artifact_token(timeframe, market) # → "features.{market}.v2"
make_funding_artifact_token(timeframe)     # → "raw.perp.funding_{tf}"
```

---

## Full Artifact Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGEST STAGE                                       │
│                                                                              │
│  Binance UM Perp                  Binance Spot                               │
│  ├── ingest_binance_um_ohlcv_1m   → raw.perp.ohlcv_1m                      │
│  ├── ingest_binance_um_ohlcv_5m   → raw.perp.ohlcv_5m                      │
│  ├── ingest_binance_um_funding     → raw.perp.funding_5m                    │
│  ├── ingest_binance_um_open_int... → raw.perp.open_interest                 │
│  ├── ingest_binance_um_liquidat... → raw.perp.liquidations                  │
│  ├── ingest_binance_um_mark_price  → raw.perp.mark_price_{tf}               │
│  ├── ingest_binance_um_book_tick   → raw.perp.book_ticker                   │
│  ├── ingest_binance_spot_ohlcv_1m  → raw.spot.ohlcv_1m                     │
│  └── ingest_binance_spot_ohlcv_5m  → raw.spot.ohlcv_5m                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                            CLEAN STAGE                                       │
│                                                                              │
│  build_cleaned_{tf}    : raw.perp.ohlcv_{tf}     → clean.perp.*             │
│  build_cleaned_{tf}_spot: raw.spot.ohlcv_{tf}    → clean.spot.*             │
│  build_basis_state_5m  : clean.perp.* + clean.spot.* → basis_state          │
│  build_tob_5m_agg      : raw.perp.book_ticker    → tob_5m                   │
│  build_tob_snapshots_1s: raw.perp.book_ticker    → tob_1s                   │
│  calibrate_execution_costs: tob data             → cost_calibration          │
│  validate_data_coverage, validate_feature_integrity, validate_context_entropy│
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                          FEATURES STAGE                                      │
│                                                                              │
│  build_features_{tf}   : clean.perp.*                                       │
│                         + optional: funding, liquidations, OI               │
│                         → features.perp.v2                                   │
│  build_features_{tf}_spot: clean.spot.*  → features.spot.v2                 │
│  build_market_context  : features.perp.v2 → context features (regimes)      │
│  build_microstructure_rollup: tob_1s → microstructure_rollup               │
│  build_universe_snapshots: clean.perp.* → metadata.universe_snapshots       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                        RUNTIME INVARIANTS STAGE                              │
│                                                                              │
│  build_normalized_replay_stream  → normalized event stream                  │
│  run_causal_lane_ticks           → causal lane validation                   │
│  run_determinism_replay_checks   → determinism assertions                   │
│  run_oms_replay_validation       → OMS replay integrity                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                       PHASE 1 ANALYSIS STAGE                                 │
│                                                                              │
│  analyze_*             : features → event detection per family              │
│                          (one analyze_* script per event family)            │
│  phase1_correlation_clustering: event episodes → correlation clusters       │
│  build_event_registry  : all event episodes → unified event registry        │
│  canonicalize_event_episodes: episodes → canonical episode format           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                      PHASE 2 DISCOVERY STAGE                                 │
│                                                                              │
│  phase2_conditional_hypotheses: event episodes + features                   │
│                                → hypothesis evaluation frames               │
│  phase2_search_engine : search space → hypothesis candidates                │
│  bridge_evaluate_phase2: hypothesis frames → scored candidates              │
│  summarize_discovery_quality: candidates → quality summary                  │
│  finalize_experiment  : all phase2 outputs → experiment manifest            │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                      RESEARCH QUALITY STAGE                                  │
│                                                                              │
│  analyze_conditional_expectancy  → conditional expectancy report            │
│  validate_expectancy_traps       → trap detection                           │
│  generate_recommendations_checklist → actionable checklist                  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                         PROMOTION STAGE                                      │
│                                                                              │
│  evaluate_naive_entry            → naive baseline for comparison            │
│  generate_negative_control_summary → negative control report                │
│  promote_candidates              → gated promotion decisions                │
│  update_edge_registry            → persists promoted edges                  │
│  update_campaign_memory          → writes to memory store                   │
│  export_edge_candidates          → exported candidate artifacts             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                      STRATEGY PACKAGING STAGE                                │
│                                                                              │
│  compile_strategy_blueprints → Blueprint YAML/JSON artifacts                │
│  build_strategy_candidates   → candidate strategy set                       │
│  select_profitable_strategies → filtered profitable set                     │
│          ↓                                                                   │
│  Live Engine (Native)                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage Contract Types

Defined in `project/contracts/pipeline_registry.py`:

### `StageFamilyContract`

Groups related stages under one owner:

```python
@dataclass(frozen=True)
class StageFamilyContract:
    family: str
    stage_patterns: tuple[str, ...]    # fnmatch patterns
    script_patterns: tuple[str, ...]   # relative script paths
```

### `StageArtifactContract`

Declares inputs and outputs for one stage:

```python
@dataclass(frozen=True)
class StageArtifactContract:
    stage_patterns: tuple[str, ...]
    inputs: tuple[str, ...]            # Required artifact tokens
    optional_inputs: tuple[str, ...]   # Optional artifact tokens
    outputs: tuple[str, ...]           # Produced artifact tokens
    external_inputs: tuple[str, ...]   # Tokens expected from external sources
```

### `ResolvedStageArtifactContract`

Runtime-resolved version with all wildcard tokens expanded for a specific run.

---

## Manifest System

Every run produces a hierarchical manifest that tracks all artifacts.

### Manifest Read Order (for trust assessment)

```
1. data/{run_id}/manifest.json          ← top-level run manifest
2. data/{run_id}/{stage}/manifest.json  ← per-stage manifests
3. data/{run_id}/{stage}/*.log          ← stage logs
4. data/{run_id}/reports/               ← report artifacts
5. docs/generated/                      ← machine-owned diagnostics
```

If any of these disagree with each other, the **disagreement is a first-class finding** and must be investigated before the run's conclusions can be trusted.

### Manifest Fields

Key fields in the run manifest:

- `run_id` — unique run identifier
- `config_digest` — hash of effective config at run time
- `data_fingerprint` — hash of input data state
- `git_commit` — source code commit at run time
- `stage_results` — per-stage completion status and artifact hashes
- `claim_map_hash` — hash of the artifact claim map
- `runtime_lineage_fields` — provenance fields for auditing

---

## Point-in-Time Correctness

All features declare a `pit_constraint`:

```yaml
provenance:
  pit_constraint: "asof <= t0"
```

This enforces that no future information can leak into feature computations at time `t0`. The `run_causal_lane_ticks` stage validates this at runtime.

---

## Cost Model in the Data Flow

Execution costs are propagated through every evaluation:

```
cost_calibration (from TOB data)
    ↓
CandidateCostEstimate (per symbol, regime, time-of-day)
    ↓
phase2 scoring: after_cost_expectancy = raw_expectancy - round_trip_cost
    ↓
Gate V1: min_after_cost_expectancy_bps = 0.1
    ↓
Promotion: cost_stress_multiplier = 2.0× (deployable), 1.5× (shadow)
    ↓
Blueprint: cost_config_digest locked at compile time
```

Default costs (from `spec/cost_model.yaml`):

- Fee: 4.0 bps per side
- Slippage: 2.0 bps per fill
- Round-trip total: **12.0 bps**

---

## Train / Validation / Test Split

The holdout integrity module (`pipelines/research/holdout_integrity.py`) enforces strict temporal splits:

- **Train** — used for hypothesis generation
- **Validation** — used for parameter selection and FDR control
- **Test** — held out; only evaluated for confirmed candidates

The splits are enforced at the data level and checked in `StageArtifactContract` reconciliation.

---

## False Discovery Rate Control

Phase 2 discovery applies FDR control via the **q-value** (Storey-Tibshirani procedure):

```python
apply_validation_multiple_testing(candidates)
```

- Max allowed q-value: **0.05** (5% FDR)
- Applied per event type × template × context combination
- `multiplicity_enable_cluster_adjusted: true` — applies cluster-adjusted FDR accounting for correlated hypotheses

---

## Hypothesis Registry

Hypotheses are stored in a structured registry:

```python
@dataclass
class Hypothesis:
    event_type: str
    canonical_family: str
    template: str
    context: dict
    side: str           # "long" | "short"
    horizon_bars: int
    entry_lag: int
    symbol_scope: list[str]
```

The `HypothesisRegistry` maps hypothesis IDs to `Hypothesis` objects and persists them as part of campaign memory.
