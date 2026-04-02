# Regime-First Testing Backlog

Generated from the current ontology and routing surfaces on 2026-04-02.

Primary sources:

- `spec/events/event_registry_unified.yaml`
- `spec/events/regime_routing.yaml`
- `spec/states/state_registry.yaml`
- `project/configs/registries/events.yaml`
- `project/configs/registries/templates.yaml`
- `project.domain.compiled_registry.get_domain_registry()`

This backlog is regime-first, not family-first. Proposal order is constrained by
the current intersection of:

1. canonical regime membership
2. regime-routed eligible templates
3. event-level compatible templates from the compiled registry

## Operating rules

- Run one canonical regime at a time.
- For each regime, use this proposal order:
  1. `discovery_a` — first 2-3 highest-signal event/template pairs
  2. `discovery_b` — next 2-3 fallback pairs in the same regime
  3. `template_fit` — compare the remaining compatible templates on the best surviving event
  4. `direction_or_event_direction` — isolate long/short or event-direction if the trigger supports it
  5. `selection_holdout` — freeze one event/template/direction/horizon for the holdout slice
- Skip any event with zero valid `event-template` intersections on the current surfaces.
- Treat context-only or filter-only regimes as support lanes, not primary alpha-discovery lanes.

## Queue Order

| Queue | Regime | Why Now | Notes |
| --- | --- | --- | --- |
| 1 | `TREND_FAILURE_EXHAUSTION` | Active workstream, recent local program memory, clean narrow follow-ups already in flight | Continue before opening a new frontier |
| 2 | `BASIS_FUNDING_DISLOCATION` | Existing held claims in edge registry; direct and inferred triggers with valid intersections | Prior repair/validation lane |
| 3 | `LIQUIDITY_STRESS` | Recommended starting regime in bounded experiment guidance; broad direct trigger set | Good discovery density |
| 4 | `POSITIONING_UNWIND_DELEVERAGING` | Compact regime with direct unwind trigger and clean reversal templates | Good after the first three |
| 5 | `VOLATILITY_TRANSITION` | One-event regime with clean template intersection | Fast bounded validation |
| 6 | `TREND_CONTINUATION` | Four tradable triggers with tight template set | Good expansion after exhaustion lane |
| 7 | `VOLATILITY_EXPANSION` | Two-event compact regime, direct/statistical pair | Narrow and interpretable |
| 8 | `STATISTICAL_STRETCH_OVERSHOOT` | Clean statistical regime with repeated mean-reversion pattern | Useful baseline family |
| 9 | `CROSS_ASSET_DESYNCHRONIZATION` | Clean but cross-asset/inferred lane; keep after single-asset lanes | More complex attribution |
| 10 | `EXECUTION_FRICTION` | Filter/abstention regime, not primary trade-generation frontier | Use as gating lane |
| 11 | `VOLATILITY_RELAXATION_COMPRESSION_RELEASE` | Single surviving routed template across all events | Narrow but limited surface |
| 12 | `REGIME_TRANSITION` | Current surface collapses to one surviving filter template | Keep behind richer regimes |
| 13 | `LIQUIDATION_CASCADE` | Valid but rare single-event regime | Run only after broader lanes |
| 14 | `POSITIONING_EXPANSION` | Blocked on current surfaces | No valid event-template intersections |
| 15 | `SCHEDULED_TEMPORAL_WINDOW` | Context-only lane | Do not run as standalone discovery |

## Proposal Order By Regime

### 1. `TREND_FAILURE_EXHAUSTION`

Use the active program lane first.

- `discovery_a`: `FALSE_BREAKOUT x false_breakout_reversal`
- `discovery_a`: `TREND_DECELERATION x false_breakout_reversal`
- `discovery_a`: `FORCED_FLOW_EXHAUSTION x exhaustion_reversal`
- `discovery_b`: `TREND_EXHAUSTION_TRIGGER x exhaustion_reversal`
- `discovery_b`: `FAILED_CONTINUATION x momentum_fade`
- `discovery_b`: `CLIMAX_VOLUME_BAR x momentum_fade`
- `template_fit`: compare `exhaustion_reversal` vs `momentum_fade` on the best non-false-break event
- `blocked`: `FLOW_EXHAUSTION_PROXY`, `LIQUIDATION_EXHAUSTION_REVERSAL`

### 2. `BASIS_FUNDING_DISLOCATION`

- `discovery_a`: `SPOT_PERP_BASIS_SHOCK x basis_repair`
- `discovery_a`: `CROSS_VENUE_DESYNC x convergence`
- `discovery_a`: `BASIS_DISLOC x mean_reversion`
- `discovery_b`: `FUNDING_NORMALIZATION_TRIGGER x mean_reversion`
- `discovery_b`: `FUNDING_PERSISTENCE_TRIGGER x mean_reversion`
- `discovery_b`: `FUNDING_EXTREME_ONSET x mean_reversion`
- `template_fit`: compare `basis_repair` vs `convergence` on `SPOT_PERP_BASIS_SHOCK` or `CROSS_VENUE_DESYNC`
- `late_fallback`: `FND_DISLOC`, `FUNDING_FLIP`

### 3. `LIQUIDITY_STRESS`

- `discovery_a`: `LIQUIDITY_VACUUM x mean_reversion`
- `discovery_a`: `LIQUIDITY_GAP_PRINT x stop_run_repair`
- `discovery_a`: `SPREAD_BLOWOUT x stop_run_repair`
- `discovery_b`: `ORDERFLOW_IMBALANCE_SHOCK x mean_reversion`
- `discovery_b`: `SWEEP_STOPRUN x stop_run_repair`
- `discovery_b`: `LIQUIDITY_SHOCK x mean_reversion`
- `template_fit`: compare `mean_reversion` vs `stop_run_repair` on the best of `LIQUIDITY_GAP_PRINT`, `SPREAD_BLOWOUT`, `LIQUIDITY_VACUUM`
- `late_fallback`: `DEPTH_COLLAPSE`, `ABSORPTION_PROXY`, `DEPTH_STRESS_PROXY`, `LIQUIDITY_STRESS_DIRECT`, `LIQUIDITY_STRESS_PROXY`, `PRICE_VOL_IMBALANCE_PROXY`, `WICK_REVERSAL_PROXY`

### 4. `POSITIONING_UNWIND_DELEVERAGING`

- `discovery_a`: `OI_FLUSH x exhaustion_reversal`
- `discovery_a`: `DELEVERAGING_WAVE x reversal_or_squeeze`
- `discovery_a`: `POST_DELEVERAGING_REBOUND x mean_reversion`
- `template_fit`: compare `exhaustion_reversal` vs `reversal_or_squeeze` vs `mean_reversion` on `OI_FLUSH`

### 5. `VOLATILITY_TRANSITION`

- `discovery_a`: `VOL_SHOCK x mean_reversion`
- `discovery_a`: `VOL_SHOCK x continuation`
- `discovery_a`: `VOL_SHOCK x trend_continuation`
- `template_fit`: rank all three on the same bounded slice
- `late_fallback`: `only_if_regime` is routed but not present in the current event-level intersection for `VOL_SHOCK`

### 6. `TREND_CONTINUATION`

- `discovery_a`: `TREND_ACCELERATION x trend_continuation`
- `discovery_a`: `RANGE_BREAKOUT x breakout_followthrough`
- `discovery_a`: `PULLBACK_PIVOT x pullback_entry`
- `discovery_b`: `SUPPORT_RESISTANCE_BREAK x breakout_followthrough`
- `template_fit`: compare `trend_continuation` vs `breakout_followthrough` on the strongest breakout-style trigger

### 7. `VOLATILITY_EXPANSION`

- `discovery_a`: `VOL_SPIKE x volatility_expansion_follow`
- `discovery_a`: `VOL_CLUSTER_SHIFT x trend_continuation`
- `template_fit`: compare `trend_continuation` vs `volatility_expansion_follow` on both events

### 8. `STATISTICAL_STRETCH_OVERSHOOT`

- `discovery_a`: `ZSCORE_STRETCH x mean_reversion`
- `discovery_a`: `GAP_OVERSHOOT x overshoot_repair`
- `discovery_a`: `OVERSHOOT_AFTER_SHOCK x overshoot_repair`
- `discovery_b`: `BAND_BREAK x mean_reversion`
- `template_fit`: compare `mean_reversion` vs `overshoot_repair` on the strongest trigger

### 9. `CROSS_ASSET_DESYNCHRONIZATION`

- `discovery_a`: `CROSS_ASSET_DESYNC_EVENT x convergence`
- `discovery_a`: `LEAD_LAG_BREAK x lead_lag_follow`
- `discovery_a`: `INDEX_COMPONENT_DIVERGENCE x desync_repair`
- `template_fit`: compare `convergence` vs `lead_lag_follow` vs `desync_repair` on the best surviving event

### 10. `EXECUTION_FRICTION`

Treat this as a defensive lane.

- `discovery_a`: `SLIPPAGE_SPIKE_EVENT x slippage_aware_filter`
- `discovery_a`: `SPREAD_REGIME_WIDENING_EVENT x tail_risk_avoid`
- `discovery_b`: `FEE_REGIME_CHANGE_EVENT x slippage_aware_filter`
- `template_fit`: compare `slippage_aware_filter` vs `tail_risk_avoid`
- `note`: `drawdown_filter` is routed at regime level but does not survive the current event-level intersection

### 11. `VOLATILITY_RELAXATION_COMPRESSION_RELEASE`

- `discovery_a`: `VOL_RELAXATION_START x pullback_entry`
- `discovery_a`: `RANGE_COMPRESSION_END x pullback_entry`
- `discovery_a`: `BREAKOUT_TRIGGER x pullback_entry`
- `note`: current surface leaves only one surviving template, so skip template-fit unless contracts change

### 12. `REGIME_TRANSITION`

Treat this as a filter/risk lane first, not a primary trade-generation regime.

- `discovery_a`: `VOL_REGIME_SHIFT_EVENT x drawdown_filter`
- `discovery_a`: `CHOP_TO_TREND_SHIFT x drawdown_filter`
- `discovery_b`: `TREND_TO_CHOP_SHIFT x drawdown_filter`
- `discovery_b`: `CORRELATION_BREAKDOWN_EVENT x drawdown_filter`
- `discovery_b`: `BETA_SPIKE_EVENT x drawdown_filter`
- `note`: all surviving intersections currently collapse to `drawdown_filter`

### 13. `LIQUIDATION_CASCADE`

- `discovery_a`: `LIQUIDATION_CASCADE x exhaustion_reversal`
- `discovery_a`: `LIQUIDATION_CASCADE x reversal_or_squeeze`
- `discovery_a`: `LIQUIDATION_CASCADE x convexity_capture`
- `template_fit`: rank the three templates on the same bounded slice

### 14. `POSITIONING_EXPANSION`

Blocked on the current surfaces.

- `blocked`: `OI_SPIKE_NEGATIVE`
- `blocked`: `OI_SPIKE_POSITIVE`
- `reason`: no valid intersection between current event-level templates and routed regime templates
- `next action`: repair or reconcile ontology/routing/compiled-registry compatibility before opening a proposal lane

### 15. `SCHEDULED_TEMPORAL_WINDOW`

Do not run as a standalone discovery regime.

- `context_only`: `FUNDING_TIMESTAMP_EVENT`
- `context_only`: `SCHEDULED_NEWS_WINDOW_EVENT`
- `context_only`: `SESSION_CLOSE_EVENT`
- `context_only`: `SESSION_OPEN_EVENT`
- `next action`: use only as an explicit context gate or exclusion axis inside another canonical regime

## Proposal Naming Pattern

Use one stable naming shape across the backlog:

- discovery: `<ASSET>_<REGIME_SHORT>_<EVENT>_DISCOVERY_<WINDOW>.yaml`
- template fit: `<ASSET>_<REGIME_SHORT>_<EVENT>_<TEMPLATE>_TEMPLATEFIT_<WINDOW>.yaml`
- direction isolate: `<ASSET>_<REGIME_SHORT>_<EVENT>_<TEMPLATE>_<DIR>_<WINDOW>.yaml`
- selection: `<ASSET>_<REGIME_SHORT>_<EVENT>_<TEMPLATE>_SELECTION_<HOLDOUT>.yaml`

## Immediate Next Bounded Action

Continue queue item `1`, `TREND_FAILURE_EXHAUSTION`, by keeping the regime fixed
and running the remaining narrow comparisons in this order:

1. `FALSE_BREAKOUT x false_breakout_reversal`
2. `TREND_DECELERATION x false_breakout_reversal`
3. `FORCED_FLOW_EXHAUSTION x exhaustion_reversal`

Do not open a new regime until that lane reaches a `keep`, `modify`, or `kill`
decision.
