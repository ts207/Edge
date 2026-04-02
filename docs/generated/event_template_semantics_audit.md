# Event Template Semantics Audit

- Status: `passed`
- Active events: `70`
- Events using default template set: `0`
- Events missing event-specific template row: `0`
- Events with unregistered templates: `0`
- Events with runtime template drops: `0`
- Events with intentional runtime suppression: `5`
- Events with operator-compatibility overrides: `0`
- Single-asset events exposing cross-asset templates: `0`
- Family templates missing runtime registration: `0`
- Lexicon templates missing runtime registration: `0`
- Runtime templates missing lexicon: `0`
- Unused runtime templates: `0`

## Default Template Inheritance

- Default template set: `['mean_reversion', 'continuation', 'trend_continuation', 'pullback_entry']`
- Events: `[]`

## Missing Event-Specific Template Rows

- Events: `[]`

## Events With Unregistered Templates

- None

## Runtime Template Drops

- None

## Intentional Runtime Suppression

- `POST_DELEVERAGING_REBOUND`: raw=['mean_reversion', 'exhaustion_reversal', 'momentum_fade', 'range_reversion', 'only_if_trend', 'drawdown_filter'], runtime=[], family=`POSITIONING_UNWIND_DELEVERAGING`, legacy=`FORCED_FLOW_AND_EXHAUSTION`
- `SEQ_FND_EXTREME_THEN_BREAKOUT`: raw=['reversal_or_squeeze', 'mean_reversion', 'continuation', 'exhaustion_reversal', 'convexity_capture', 'only_if_funding', 'only_if_oi', 'tail_risk_avoid'], runtime=[], family=`BASIS_FUNDING_DISLOCATION`, legacy=`POSITIONING_EXTREMES`
- `SEQ_LIQ_VACUUM_THEN_DEPTH_RECOVERY`: raw=['mean_reversion', 'stop_run_repair', 'overshoot_repair', 'continuation', 'only_if_liquidity', 'slippage_aware_filter'], runtime=[], family=`LIQUIDITY_STRESS`, legacy=`LIQUIDITY_DISLOCATION`
- `SEQ_OI_SPIKEPOS_THEN_VOL_SPIKE`: raw=['reversal_or_squeeze', 'mean_reversion', 'continuation', 'exhaustion_reversal', 'convexity_capture', 'only_if_funding', 'only_if_oi', 'tail_risk_avoid'], runtime=[], family=`POSITIONING_EXPANSION`, legacy=`POSITIONING_EXTREMES`
- `SEQ_VOL_COMP_THEN_BREAKOUT`: raw=['mean_reversion', 'continuation', 'trend_continuation', 'volatility_expansion_follow', 'pullback_entry', 'only_if_regime'], runtime=[], family=`VOLATILITY_RELAXATION_COMPRESSION_RELEASE`, legacy=`VOLATILITY_TRANSITION`

## Operator Compatibility Overrides

- None

## Single-Asset Events With Cross-Asset Templates

- None

## Template Vocabulary Drift

- family_templates_missing_runtime_registration: `[]`
- lexicon_templates_missing_runtime_registration: `[]`
- runtime_templates_missing_lexicon: `[]`
- unused_runtime_templates: `[]`

