# Feature Catalog

This note is the operator-facing companion to
[feature_registry.py](/home/tstuv/workspace/trading/EDGEE/project/core/feature_registry.py).

Use it to answer:

1. What canonical feature already exists?
2. What does it mean?
3. Which stage owns it?

The code registry is still the source of truth. This note is the quick reference.

## Core Price And Basis Features

| Feature | Meaning | Units | Stage |
| --- | --- | --- | --- |
| `basis_bps` | Perp versus spot basis in basis points | `bps` | `build_features` |
| `basis_zscore` | Rolling z-score of `basis_bps` | `zscore` | `build_features` |
| `spread_bps` | Estimated spread proxy from microstructure inputs | `bps` | `build_features` |
| `spread_zscore` | Rolling z-score of `spread_bps` | `zscore` | `build_features` |
| `rv_96` | Canonical lagged realized volatility over 96 bars | `volatility` | `build_features` |
| `rv_pct_17280` | Long-lookback percentile rank of `rv_96` | `percentile` | `build_features` |

## Funding And Microstructure Features

| Feature | Meaning | Units | Stage |
| --- | --- | --- | --- |
| `funding_rate_scaled` | Canonical funding rate aligned to bar timestamps | `decimal_rate` | `build_features` |
| `funding_abs_pct` | Percentile rank of absolute funding magnitude | `percentile` | `build_features` |
| `imbalance` | Buy-versus-sell pressure imbalance | `ratio` | `build_features` |
| `micro_depth_depletion` | Depth-depletion proxy for stressed liquidity | `ratio` | `build_features` |

## Canonical Market-State Features

These are the main reuse surface for detectors. When a detector can use them, it should
prefer them over rebuilding adjacent state logic inline.

| Feature | Meaning | Units | Stage |
| --- | --- | --- | --- |
| `ms_vol_state` | Canonical volatility state | `state_code` | `build_market_context` |
| `ms_liq_state` | Canonical liquidity state | `state_code` | `build_market_context` |
| `ms_oi_state` | Canonical open-interest state | `state_code` | `build_market_context` |
| `ms_funding_state` | Canonical funding state | `state_code` | `build_market_context` |
| `ms_trend_state` | Canonical trend/chop state | `state_code` | `build_market_context` |
| `ms_spread_state` | Canonical spread state | `state_code` | `build_market_context` |
| `ms_context_state_code` | Encoded composite state across the main dimensions | `state_code` | `build_market_context` |

## Funding-Persistence Surface

| Feature | Meaning | Units | Stage |
| --- | --- | --- | --- |
| `fp_active` | Funding-persistence active flag | `flag` | `build_market_context` |
| `fp_age_bars` | Age of the active funding-persistence state | `bars` | `build_market_context` |
| `fp_severity` | Funding-persistence severity score | `score` | `build_market_context` |

## Working Rules

- Prefer canonical named features before adding detector-local rolling state.
- If a detector needs a new reusable state, add it to the feature registry first.
- If a feature is detector-specific and not reusable, keep it local and do not pollute the registry.
- Treat the registry as the contract surface and this note as the quick reference.

## Shared Helper Surfaces

Some reusable logic now lives below the registry itself:

- [context_guards.py](/home/tstuv/workspace/trading/EDGEE/project/features/context_guards.py)
  - canonical `ms_*` state parsing and optional guard construction
- [rolling_thresholds.py](/home/tstuv/workspace/trading/EDGEE/project/features/rolling_thresholds.py)
  - lagged rolling quantile thresholds for causal detector comparisons

Detectors should prefer these helper surfaces before re-implementing the same rolling-state
or lagged-threshold logic inline.
