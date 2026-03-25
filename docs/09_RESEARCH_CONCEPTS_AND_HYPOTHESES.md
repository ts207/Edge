# Edge — Research Concepts, Hypotheses & Backlog

## Research Concept Framework

The research backlog (`research_backlog.csv`) catalogs pre-registered research claims that form the foundation of the platform's research program. Each claim maps to:

- A **concept** (the market phenomenon being studied)
- A **candidate type** (event, feature, or evaluation)
- A **target gate** (which pipeline gate it's aiming for: E-1, V1, Bridge)
- An **artifact** location in the spec tree
- A set of **features** required
- An **operationalization condition**

---

## Bootstrap Research Concepts

These are the foundational concepts built into the platform at inception:

| Concept ID | Type | Gate | Claim |
|---|---|---|---|
| `C_EVENT_DEFINITIONS` | event / mechanistic | E-1 | Events are deterministic t0 anchors; states are derived downstream. Metrics: frequency, co_occurrence |
| `C_EVENT_REGISTRY` | event / mechanistic | E-1 | Deterministic, versioned taxonomy of tradable market situations. Metrics: prevalence, determinism |
| `C_LIQUIDITY_MEAN_REVERSION` | event / mechanistic | E-1 | Price reverts to fair value after liquidity shocks. P(revert within 30m \| basis_spike > 3) > 0.7 |
| `C_MICROSTRUCTURE_METRICS` | feature / mechanistic | V1 | Roll spread, VPIN, Amihud quantify liquidity and trade toxicity. roll_spread_bps > 0 |
| `C_TREND_EXHAUSTION` | event / mechanistic | E-1 | Mature trends likely to reverse. P(reversal \| streak ≥ 5) > 0.6 |
| `C_VOLATILITY_STATE_TRANSITIONS` | event / mechanistic | E-1 | Cyclic compression → expansion → exhaustion → reset. autocorrelation(rv_bps, 1) > 0.4 |
| `C_CONTEXT_DELTAS` | feature / mechanistic | V1 | State trajectory leading up to event matters. all(input_ts <= t0) |
| `C_CONTEXT_INTERACTIONS` | feature / mechanistic | V1 | Edges manifest when multiple conditions align. sharpe(A+B) > 2 × sharpe(A) |
| `C_EXECUTION_COST_MODEL` | execution / mechanistic | Bridge | Explicit fees + implicit frictions via implementation shortfall. impact(2Q) < 2 × impact(Q) |
| `C_SESSION_MICROSTRUCTURE` | feature / mechanistic | V1 | Session-stratified liquidity dynamics. E[NY_range \| Asia_range_pct < 0.3] > E[NY_range] |
| `C_ML_TRADING_MODELS` | evaluation / mechanistic | V1 | ML models for regime detection with PIT constraints. performance ≈ 0 on randomized timestamps |
| `C_MULTIPLICITY_CONTROL` | evaluation / mechanistic | V1 | FDR correction when testing many hypotheses. q_value ≤ 0.05 |
| `C_STRATEGY_BACKTEST` | evaluation / mechanistic | V1 | Long-horizon simulation with parameter sweeps. 80% of neighborhood profitable |
| `C_VALIDATION` | evaluation / mechanistic | V1 | Conditional returns → edges via cross-validation + regime partitioning. expectancy > 0 in 3+ regimes |
| `C_DATA_CONTRACTS` | execution / mechanistic | Bridge | Venue-specific mechanics and schemas. conformance_rate |
| `C_DATA_SCHEMA` | execution / mechanistic | Bridge | Universal labeling schema. has(timestamp, symbol, run_id) |
| `C_PROVENANCE_REPLAY` | execution / mechanistic | Bridge | Deterministic replay from versioned inputs. valid SHA and hashes present |
| `C_EVALUATION_MODE` | evaluation / mechanistic | V1 | Boolean gate controlling claim artifact production |
| `C_INVARIANTS` | evaluation / mechanistic | V1 | Structural constraints as sanity checks. basis within carry bounds > 90% |

---

## Stress Scenarios (`spec/grammar/stress_scenarios.yaml`)

Pre-defined market stress scenarios used for robustness testing of promoted strategies:

| Scenario | Condition | Description |
|---|---|---|
| `HIGH_VOL_SHOCK` | `rv_pct_17280 > 0.9` | Top decile realized volatility |
| `WIDE_SPREAD` | `spread_zscore > 2.0` | Bid-ask spread 2σ above median |
| `EXTREME_FUNDING` | `funding_rate > 0.0002` | Funding above 0.02% per 8h |
| `POST_CRASH` | `logret_1 < -0.002` | Following a 20bps+ down bar |
| `LIQUIDATION_ACTIVE` | `liquidation_count > 0` | Any liquidation activity in bar |

Strategies must demonstrate positive after-cost expectancy under these conditions to be considered deployment-relevant.

---

## Pre-Registered Hypothesis: H_LIFT_STATE_CONDITIONED_V1  ?why is this repeated again with no context or logic, why is it here, what does it do

The most prominent pre-registered hypothesis in the repo:

**Claim:** State-conditioned entries deliver a statistically significant positive lift of >10 bps in after-cost expectancy versus unconditional entries, for the same (event_type, rule_template, horizon) group.

**Registered:** 2026-02-20  
**Status:** active

**Measurement basis:**

- After-cost only (fees + slippage + funding carry deducted)
- Per-group scope: (symbol, event_type, rule_template, horizon)
- Baseline: unconditional entries, min 500 events
- Conditioned: any single regime condition (e.g., `vol_regime_high`, `carry_pos`), min 200 events
- Cost config must match the digest locked in the blueprint lineage

**Enforcement:** `evaluation_guard.py` checks this file is present and unmodified before writing `lift_claim_report.parquet` or `oos_claim_report.json`.

---

## Multiplicity Taxonomy (`spec/multiplicity/taxonomy.yaml`)

Defines the full family → event → state → template mapping as an ontological model.

Key structure per family:

```yaml
LIQUIDITY_DISLOCATION:
  description: "Microstructure imbalance and liquidity withdrawal/recovery dynamics."
  events: [LIQUIDITY_VACUUM, LIQUIDITY_SHOCK, DEPTH_COLLAPSE, SPREAD_BLOWOUT, ...]
  states: [LOW_LIQUIDITY_STATE, REFILL_LAG_STATE, SPREAD_ELEVATED_STATE, ...]
  templates: [mean_reversion, stop_run_repair, overshoot_repair, ...]
  runtime_templates: [...]   # Conservative subset for current execution paths
```

The taxonomy is the source of truth for which events, states, and templates belong to each family. It is reconciled against `spec/grammar/family_registry.yaml` by `validate_registry_consistency()`.

---

## Hypothesis Search Space (`spec/search_space.yaml`)

The search space defines the legal hypothesis combinations for Phase 2 discovery.

### Trigger Quality Annotations

Events are annotated with their information gain (IG) from prior research:

| Quality | Example Event | IG Score |
|---|---|---|
| HIGH | `LIQUIDATION_CASCADE` | 0.000467 |
| MODERATE | `OVERSHOOT_AFTER_SHOCK` | 0.000226 |
| LOW | `LIQUIDITY_VACUUM` | 0.000134 |

### Search Phases

Defined search configurations in `spec/search/`:

| File | Purpose |
|---|---|
| `search_phase1.yaml` | Phase 1 search configuration |
| `search_phase2.yaml` | Phase 2 broad search |
| `search_phase3.yaml` | Phase 3 confirmatory search |
| `search_full.yaml` | Full search across all triggers |
| `search_synthetic_truth.yaml` | Synthetic truth validation search |
| `search_benchmark_*.yaml` | 10 benchmark-specific search configs |

### Benchmark Search Configs

| Benchmark | Focus |
|---|---|
| `search_benchmark_basis_disloc_synth.yaml` | BASIS_DISLOC on synthetic |
| `search_benchmark_execution.yaml` | Execution quality |
| `search_benchmark_false_breakout.yaml` | FALSE_BREAKOUT |
| `search_benchmark_false_breakout_quality_boundary.yaml` | Quality boundary |
| `search_benchmark_fnd_disloc.yaml` | FND_DISLOC |
| `search_benchmark_liquidity_gap.yaml` | Liquidity gap |
| `search_benchmark_positioning.yaml` | Positioning extremes |
| `search_benchmark_positioning_v2.yaml` | Positioning v2 |
| `search_benchmark_vol_shock.yaml` | VOL_SHOCK |
| `search_benchmark_zscore_stretch_live.yaml` | ZSCORE_STRETCH live |

---

## Proposal Templates (`spec/proposals/`)

Pre-configured proposal examples for common use cases:

| File | Description |
|---|---|
| `btc_2021_2m_run.yaml` | BTC 2021 data, 2m timeframe run |
| `btc_synthetic_6m_2021_bull.yaml` | BTC synthetic 6-month 2021 bull regime |
| `comprehensive_synthetic_run.yaml` | Multi-regime comprehensive synthetic run |

---

## Strategy Templates (`spec/templates/`)

### `event_template_registry.yaml`

The authoritative runtime template configuration (~17KB). Defines for each event type which templates are active, their parameter bounds, and their conditions.

**Template categories:**

- **Mean reversion:** `mean_reversion`, `overshoot_repair`, `stop_run_repair`
- **Trend-following:** `continuation`, `trend_continuation`, `breakout_followthrough`
- **Volatility:** `volatility_expansion_follow`, `structural_regime_shift`
- **Positioning:** `reversal_or_squeeze`, `exhaustion_reversal`, `convexity_capture`
- **Flow:** `momentum_fade`, `range_reversion`, `pullback_entry`
- **Desync:** `desync_repair`, `convergence`, `basis_repair`, `lead_lag_follow`
- **Filters:** `only_if_liquidity`, `only_if_regime`, `only_if_funding`, `only_if_oi`, `tail_risk_avoid`, `slippage_aware_filter`, `drawdown_filter`

---

## Hypothesis Verb Lexicon (`spec/hypotheses/template_verb_lexicon.yaml`)

A structured vocabulary (~12KB) that maps template types to their:

- Entry verb (what the strategy does at event time)
- Exit verb (how the strategy exits)
- Context requirements (what regime conditions are required)
- Sizing context (how position size is determined)

This enforces consistency in hypothesis language across all templates and families.

---

## Historical Universe (`spec/historical_universe.csv`)

Single-entry CSV defining the canonical historical test universe:

```
symbols
BTCUSDT
```

(Currently single-symbol; multi-symbol extension is supported by the platform.)

---

## Copula Pairs (`spec/copula_pairs.csv`)

Defines instrument pairs for copula-based statistical arbitrage strategies:

```
BTCUSDT,ETHUSDT
```

Used by `COPULA_PAIRS_TRADING` event detector.

---

## Conductor Notes (`conductor/fix_directional_gating.md`)

The `conductor/` directory holds structural fix notes and decision records. Currently contains guidance on fixing directional gating issues in the promotion pipeline — documenting a known architectural decision point.
