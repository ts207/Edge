# Edge — Spec & Ontology Reference

## Overview

All research primitives in EDGEE are defined declaratively in `spec/` as YAML files. These files are the **authoritative source** of what events, features, states, templates, and gates exist. The `project/spec_registry/` package loads them into Python at startup.

---

## 1. Events (`spec/events/`)

69 active event specs are currently registered, each assigned to one of 10 canonical families. The ontology audit currently reconciles 69 implemented events, 60 canonical entries, and 70 taxonomy entries, with `ABSORPTION_EVENT` remaining as the single planned backlog item.

### Event YAML Schema

```yaml
event_type: VOL_SHOCK                      # Unique event identifier
synthetic_coverage: uncovered  ?what does it do            # covered | uncovered
active: true
status: validated   ?how and why                       # validated | experimental | deprecated
canonical_family: VOLATILITY_TRANSITION    # One of the 10 canonical families
reports_dir: vol_shock_relaxation          # Output directory
events_file: vol_shock_relaxation_events.parquet
signal_column: vol_shock_relaxation_event  # Boolean column name in output
detector_contract: true                    # Whether a formal detector spec exists

parameters:                                # Detector-specific numeric parameters
  shock_quantile: 0.90
  lookback_window: 288
  cooldown_bars: 12
  merge_gap_bars: 0

detector:
  signal_definition: >                     # Human-readable definition
    ...
  formula: |                               # Computational formula
    realized_vol[i] = std(log_returns[i-N..i]) * sqrt(bars_per_day)
    ...
```

> [!IMPORTANT]
> **Parameter Decoupling Rule:** All detector logic in Python (`project/events/families/`) **must** dynamically fetch thresholds, windows, and quantiles from this YAML `parameters` block using `params.get("key", default)`. Hardcoding numerical thresholds directly in Python event subclasses is strictly forbidden to prevent configuration drift.

### Complete Event Catalog by Family

The family list below is maintained for navigation; exact counts are tracked in the generated ontology audit to avoid doc drift.

**LIQUIDITY_DISLOCATION**
`ABSORPTION_PROXY`, `DEPTH_COLLAPSE`, `DEPTH_STRESS_PROXY`, `LIQUIDITY_GAP_PRINT`, `LIQUIDITY_SHOCK`, `LIQUIDITY_STRESS_DIRECT`, `LIQUIDITY_STRESS_PROXY`, `LIQUIDITY_VACUUM`, `SPREAD_BLOWOUT`, `SPREAD_REGIME_WIDENING_EVENT`, `SWEEP_STOPRUN`, and others.

**POSITIONING_EXTREMES**
`FUNDING_EXTREME_ONSET`, `FUNDING_FLIP`, `FUNDING_NORMALIZATION_TRIGGER`, `FUNDING_PERSISTENCE_TRIGGER`, `FUNDING_TIMESTAMP_EVENT`, `LIQUIDATION_CASCADE`, `OI_FLUSH`, `OI_SPIKE_NEGATIVE`, `OI_SPIKE_POSITIVE`, `POST_DELEVERAGING_REBOUND`, and others.

**FORCED_FLOW_AND_EXHAUSTION**
`CLIMAX_VOLUME_BAR`, `DELEVERAGING_WAVE`, `FLOW_EXHAUSTION_PROXY`, `FORCED_FLOW_EXHAUSTION`, `MOMENTUM_DIVERGENCE_TRIGGER`, `TREND_EXHAUSTION_TRIGGER`, `WICK_REVERSAL_PROXY`, and others.

**STATISTICAL_DISLOCATION**
`BAND_BREAK`, `BASIS_DISLOC`, `FND_DISLOC`, `GAP_OVERSHOOT`, `OVERSHOOT_AFTER_SHOCK`, `PRICE_VOL_IMBALANCE_PROXY`, `ZSCORE_STRETCH`, and others.

**VOLATILITY_TRANSITION**
`BREAKOUT_TRIGGER`, `RANGE_COMPRESSION_END`, `SLIPPAGE_SPIKE_EVENT`, `VOL_CLUSTER_SHIFT`, `VOL_REGIME_SHIFT_EVENT`, `VOL_RELAXATION_START`, `VOL_SHOCK`, `VOL_SPIKE`, and others.

**TREND_STRUCTURE**
`CHOP_TO_TREND_SHIFT`, `FAILED_CONTINUATION`, `FALSE_BREAKOUT`, `PULLBACK_PIVOT`, `RANGE_BREAKOUT`, `SUPPORT_RESISTANCE_BREAK`, `TREND_ACCELERATION`, `TREND_DECELERATION`, `TREND_TO_CHOP_SHIFT`, and others.

**REGIME_TRANSITION**
`BETA_SPIKE_EVENT`, `CORRELATION_BREAKDOWN_EVENT`, and others.

**INFORMATION_DESYNC**
`CROSS_VENUE_DESYNC`, `INDEX_COMPONENT_DIVERGENCE`, `LEAD_LAG_BREAK`, `SPOT_PERP_BASIS_SHOCK`, and others.

**TEMPORAL_STRUCTURE**
`FEE_REGIME_CHANGE_EVENT`, `NO_FEE_IMPACT`, `SCHEDULED_NEWS_WINDOW_EVENT`, `SESSION_CLOSE_EVENT`, `SESSION_OPEN_EVENT`, and others.

**EXECUTION_FRICTION**
`FEE_REGIME_CHANGE_EVENT`, `SLIPPAGE_SPIKE_EVENT`, `SPREAD_REGIME_WIDENING_EVENT`, and others.

### Shared Detector Constraint

Proxy-tier events intentionally share detector implementations across multiple event types. This is a deliberate design choice to maintain a narrow attribution surface at the detection layer:

| Detector Class | Events Covered |
| --- | --- |
| `PriceVolImbalanceProxyDetector` | `ORDERFLOW_IMBALANCE_SHOCK`, `PRICE_VOL_IMBALANCE_PROXY` |
| `WickReversalProxyDetector` | `SWEEP_STOPRUN`, `WICK_REVERSAL_PROXY` |
| `DepthStressProxyDetector` | `DEPTH_COLLAPSE`, `DEPTH_STRESS_PROXY` |
| `FlowExhaustionDetector` | `FLOW_EXHAUSTION_PROXY`, `FORCED_FLOW_EXHAUSTION` |

This means these events are not independently distinguishable at the detection layer. Research attribution must account for this shared implementation constraint.

---

## 2. Features (`spec/features/` and `spec/ontology/features/`)

34 feature families. Each YAML file defines inputs, outputs, formulas, and provenance.

### Feature YAML Schema

```yaml
feature_family: volatility
version: 1.0.0
base_timeframe: 1m
inputs:
  - dataset: perp_ohlcv_1m
    columns: [high, low, close]
features:
  - name: realized_vol_bps
    description: Annualized realized volatility in basis points
    formula: std(log_returns) * sqrt(periods_per_year) * 10000
    params: {window: 60, annualization_periods: 525600}
provenance:
  pit_constraint: "asof <= t0"   # Point-in-time correctness rule
  source_id: "R12"               # Research claim source
  claim_id: ["CL_0075", ...]
```

### Feature Catalog- ?are detectors and other modules using these features effectively and correctly? | Feature | Family | Description
|---|---|---|
| `amihud` | microstructure | Amihud illiquidity ratio (abs return / dollar volume) |
| `atr` | volatility | Average True Range |
| `auc` | evaluation | Area under curve for strategy returns |
| `basis` | derivatives | Perp vs. spot basis in bps (`basis_bps`, `basis_zscore`) |
| `carry_state` | regime | Carry state classification (pos/neg/neutral) |
| `context_deltas` | context | Rate-of-change context features |
| `correlation` | cross-asset | Rolling correlation between instruments |
| `expected_shortfall` | risk | Expected shortfall / CVaR |
| `funding` | derivatives | Perpetual funding rate |
| `h1_2` | statistical | H1/H2 statistical test features |
| `impact` | microstructure | Price impact metrics |
| `kyle` | microstructure | Kyle's lambda (price impact coefficient) |
| `liquidity_reversion` | microstructure | Liquidity mean reversion signal |
| `macd` | trend | Moving average convergence/divergence |
| `mae` | evaluation | Maximum adverse excursion |
| `market_depth` | microstructure | Order book depth metrics |
| `microstructure` | microstructure | Roll spread, Amihud, VPIN composite |
| `oi` | derivatives | Open interest raw and delta |
| `open_interest` | derivatives | OI with regime context |
| `order_book` | microstructure | Bid/ask imbalance, depth ratios |
| `quoted_spread` | microstructure | Quoted bid-ask spread in bps |
| `random_forest` | ML | Random forest signal features |
| `realized_vol` | volatility | Realized volatility (rolling std of log returns) |
| `rmse` | evaluation | Root mean square error of model fits |
| `roll` | microstructure | Roll spread estimator |
| `rsi` | momentum | Relative Strength Index |
| `session_features` | temporal | Session-level volume/return profiles |
| `sharpe` | evaluation | Rolling Sharpe ratio |
| `slippage` | execution | Realized slippage estimates |
| `spread` | microstructure | Effective spread metrics |
| `trend_exhaustion` | trend | Trend exhaustion composite score |
| `vol_regime` | regime | Volatility regime classification (high/low) |
| `volatility` | volatility | `realized_vol_bps`, `atr_percentile`, `vol_compression_flag` |
| `vpin` | microstructure | Volume-synchronized probability of informed trading |

---

## 3. Market States (`spec/states/` and `spec/ontology/states/`)

19 named market states, each tied to a canonical event family.

### State YAML Schema

```yaml
state_id: REFILL_LAG_STATE
family: LIQUIDITY_DISLOCATION
source_event_type: LIQUIDITY_VACUUM
activation_rule: elapsed_bars <= refill_horizon AND depth_recovery_ratio < refill_threshold
decay_rule: exit when depth_recovery_ratio >= refill_threshold OR elapsed_bars > refill_horizon
features_required:
  - market_depth
  - quote_volume
  - spread_bps
allowed_templates:
  - mean_reversion
  - stop_run_repair
  - continuation
```

### State Catalog | State | Source Event | Family |
|---|---|---|
| `AFTERSHOCK_STATE` | Post-shock periods | VOLATILITY_TRANSITION |
| `CHOP_STATE` | Range-bound, no trending | REGIME_TRANSITION |
| `COMPRESSION_STATE` | Pre-breakout compression | VOLATILITY_TRANSITION |
| `CROWDING_STATE` | Extreme positioning | POSITIONING_EXTREMES |
| `DELEVERAGING_STATE` | Active forced deleveraging | FORCED_FLOW_AND_EXHAUSTION |
| `FUNDING_NORMALIZATION_STATE` | Funding reverting to zero | POSITIONING_EXTREMES |
| `FUNDING_PERSISTENCE_STATE` | Persistently elevated funding | POSITIONING_EXTREMES |
| `HIGH_FRICTION_STATE` | Elevated spread/slippage | LIQUIDITY_DISLOCATION |
| `HIGH_VOL_REGIME` | Realized vol above threshold | VOLATILITY_TRANSITION |
| `LOW_LIQUIDITY_STATE` | Depth below normal | LIQUIDITY_DISLOCATION |
| `LOW_VOL_REGIME` | Compressed realized vol | VOLATILITY_TRANSITION |
| `OVERSHOOT_STATE` | Price extended beyond fair value | STATISTICAL_DISLOCATION |
| `POST_EXPANSION_STATE` | After breakout expansion | TREND_STRUCTURE |
| `REFILL_LAG_STATE` | Post-vacuum depth recovery lag | LIQUIDITY_DISLOCATION |
| `RELAXATION_STATE` | Vol relaxing after shock | VOLATILITY_TRANSITION |
| `STRETCHED_STATE` | Z-score stretched | STATISTICAL_DISLOCATION |
| `TRENDING_STATE` | Confirmed directional trend | TREND_STRUCTURE |
| `carry_state` | Persistent funding carry | POSITIONING_EXTREMES |
| `vol_regime` | Rolling vol percentile regime | VOLATILITY_TRANSITION |

---

## 4. Grammar & Sequences (`spec/grammar/`)

### Allowed Templates Per Family (`family_registry.yaml`)

Templates constrain what strategy shapes are legal for each event family: | Family | Allowed Templates |
|---|---|
| LIQUIDITY_DISLOCATION | `mean_reversion`, `continuation`, `stop_run_repair`, `overshoot_repair`, `only_if_liquidity`, `slippage_aware_filter`, `liquidity_replenishment` |
| VOLATILITY_TRANSITION | `mean_reversion`, `continuation`, `trend_continuation`, `volatility_expansion_follow`, `pullback_entry`, `only_if_regime`, `structural_regime_shift` |
| POSITIONING_EXTREMES | `reversal_or_squeeze`, `mean_reversion`, `continuation`, `exhaustion_reversal`, `convexity_capture`, `only_if_funding`, `only_if_oi`, `tail_risk_avoid` |
| FORCED_FLOW_AND_EXHAUSTION | `mean_reversion`, `exhaustion_reversal`, `momentum_fade`, `range_reversion`, `only_if_trend`, `drawdown_filter` |
| TREND_STRUCTURE | `breakout_followthrough`, `false_breakout_reversal`, `pullback_entry`, `trend_continuation`, `continuation`, `only_if_trend` |
| STATISTICAL_DISLOCATION | `mean_reversion`, `overshoot_repair`, `tail_risk_avoid` |
| REGIME_TRANSITION | `only_if_regime`, `continuation`, `mean_reversion`, `drawdown_filter`, `tail_risk_avoid` |
| INFORMATION_DESYNC | `desync_repair`, `convergence`, `basis_repair`, `lead_lag_follow`, `divergence_continuation` |
| TEMPORAL_STRUCTURE | `mean_reversion`, `continuation`, `tail_risk_avoid`, `only_if_no_news_window` |
| EXECUTION_FRICTION | `slippage_aware_filter`, `tail_risk_avoid`, `only_if_liquidity` |

### Named Event Sequences (`sequence_registry.yaml`)  ?explain the logic and instructions as it is most important alpha source

Multi-event temporal patterns that can be used as composite triggers:

| Sequence | Events (ordered) | Max Gaps (bars) | Mode |
|---|---|---|---|
| `crowding_unwind` | `FUNDING_EXTREME_ONSET` → `OI_FLUSH` → `LIQUIDATION_CASCADE` | [6, 12] | ordered_strict |
| `compression_breakout` | `RANGE_COMPRESSION_END` → `BREAKOUT_TRIGGER` → `FALSE_BREAKOUT` | [12, 6] | ordered_strict |
| `liquidity_stress_repair` | `SPREAD_BLOWOUT` → `ABSORPTION_EVENT` | [6] | ordered_strict |

#### Sequence Detector Implementation Status

Four sequence event types exist as spec entries:
- `SEQ_FND_EXTREME_THEN_BREAKOUT`
- `SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY`
- `SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE`
- `SEQ_VOL_COMP_THEN_BREAKOUT`

These are currently implemented as stubs via the generic `EventSequenceDetector` wrapper class. They are registered and will run, but use a generic composite pattern rather than specialized detection logic. They are marked as `experimental` status in the spec.

---

## 5. Promotion Gates (`spec/gates.yaml`)

### Gate E1 — Event Quality Gate | Criterion | Value |
|---|---|
| Min prevalence per 10k bars | 1.0 |
| Max prevalence per 10k bars | 500.0 |
| Min join rate | 0.99 |
| Max 5-bar clustering | 0.20 |

### Gate V1 — Phase 2 Statistical Gate | Criterion | Value |
|---|---|
| Max q-value (FDR) | 0.05 |
| Min after-cost expectancy | 0.1 bps |
| Conservative cost multiplier | 1.5× |
| Require sign stability | true |
| Min sample size | 50 |
| Regime ESS min per regime | 1.0 |
| Quality floor (strict) | 0.66 |
| Quality floor (fallback) | 0.66 |

### Promotion Confirmatory Gates (P3)

**Deployable tier:** | Criterion | Value |
|---|---|
| Max q-value | 0.05 |
| Min OOS ESS | 50 |
| Min OOS event count | 50 |
| Require independent test significance | true |
| Max posterior error | 0.02 |
| Cost stress multiplier | 2.0× |
| Latency stress bars | 2 |
| Max overlap concentration | 0.50 |
| Min regimes supported | 2 |
| Min ESS per regime | 20 |
| Require regime stability | true |

**Shadow tier:**  ?how this tier is used | Criterion | Value |
|---|---|
| Max q-value | 0.10 |
| Min OOS ESS | 20 |
| Min OOS event count | 20 |
| Require sign consistency | true |
| Cost stress multiplier | 1.5× |
| Latency stress bars | 1 |
| Min regimes supported | 1 |
| Min ESS per regime | 10 |

---

## 6. Global Defaults (`spec/global_defaults.yaml`)

```yaml
defaults:
  horizons: ["5m", "15m", "60m"]
  rule_templates: ["mean_reversion", "continuation", "trend_continuation", "pullback_entry"]
  conditioning:
    vol_regime: ["high", "low"]
    carry_state: ["pos", "neg", "neutral"]
    funding_bps: ["extreme_pos", "extreme_neg"]
    ms_trend_state: ["0", "1", "2"]
    ms_spread_state: ["0", "1"]
    severity_bucket: ["minor", "moderate", "extreme"]  ?explain this severity bucket
```

---

## 7. Cost Model (`spec/cost_model.yaml`) | Parameter | Default |
|---|---|
| Fee (per side) | 4.0 bps |
| Slippage (per fill) | 2.0 bps |
| Round-trip cost | 12.0 bps (2 × fee + 2 × slippage) |

---

## 8. Blueprint Policies (`spec/blueprint_policies.yaml`)

Governs stop/target calibration and position sizing defaults: | Parameter | Value |
|---|---|
| Time stop range | 4–192 bars |
| Stop percentile | 75th |
| Target percentile | 60th |
| Target/stop min ratio | 1.1 |
| Vol target (sizing) | 12% annualized |
| Base risk per trade | 0.3% |
| High-robustness risk per trade | 0.4% |
| Default execution mode | market |
| Default urgency | aggressive |

---

## 9. Runtime Lanes (`spec/runtime/lanes.yaml`)

The live engine runs two processing lanes with strict causal separation: | Lane | Cadence | Purpose | Alpha | Execution |
|---|---|---|---|---|
| `alpha_5s` | 5 seconds | Alpha signal computation | ✓ | ✗ |  ?explain the alpha signal computation
| `exec_1s` | 1 second | Order management | ✗ | ✓ |

The firewall (`spec/runtime/firewall.yaml`) enforces that alpha computations cannot observe post-trade execution state.

---

## 10. Runtime Firewall (`spec/runtime/firewall.yaml`) | Role | Allowed Provenance | Can See Exec State |
|---|---|---|
| `alpha` | market, calendar, quality | No |
| `events` | market, calendar, quality | No |
| `execution` | execution, market, quality | Yes (limited fields) |

**Hard constraint:** `forbid_posttrade_for_alpha: true` — no feedback from fills into alpha signals.

---

## 11. Search Space (`spec/search_space.yaml`)

The hypothesis search space defines which triggers, templates, contexts, horizons, and directions are valid combinations for Phase 2 discovery.

**Trigger types:**

- `events` — discrete market events (44 listed in search space)  ?why these counts are different
- `states` — regime/structural states
- `transitions` — state → state transitions
- `feature_predicates` — continuous feature conditions

**Notable annotations in search space:**  ?explain

- `[QUALITY: HIGH]` — `LIQUIDATION_CASCADE` (IG 0.000467)
- `[QUALITY: MODERATE]` — `OVERSHOOT_AFTER_SHOCK` (IG 0.000226)
- `[QUALITY: LOW]` — `LIQUIDITY_VACUUM` (IG 0.000134)

---

## 12. Pre-Registered Hypothesis (`spec/hypotheses/lift_state_conditioned_v1.yaml`)  ?why this specific whats the use, remove if not important

An example of a formally pre-registered hypothesis (required before any 60-day validation run):

- **ID:** `H_LIFT_STATE_CONDITIONED_V1`
- **Claim:** State-conditioned entries deliver >10 bps lift in after-cost expectancy vs. unconditional entries
- **Scope:** Per (symbol, event_type, rule_template, horizon) group
- **Baseline:** Unconditional entries, min 500 events
- **Conditioned:** Any condition_key != "all", min 200 events
- **Measurement:** After-cost only (not gross); uses locked cost_config_digest from blueprint lineage
