# Data And Feature Layer Plan

This note records the current improvement plan for the ingest, clean, and feature surfaces.

## Why This Matters

The current repository already has strong stage boundaries:

- ingest stages collect raw OHLCV, funding, OI, and liquidation data
- clean stages align bars and funding onto canonical timestamps
- feature stages derive basis, spread, volatility, funding, and microstructure features

That structure is good. The main remaining risk is not missing architecture. It is hidden data drift.

Bad data can currently become:

1. valid-looking cleaned bars
2. valid-looking feature tables
3. detector inputs that appear trustworthy
4. incorrect events and false research conclusions

## Current Strengths

- downstream detectors mostly assume numeric, aligned inputs
- `build_cleaned_bars` already computes `is_gap` and `gap_len`
- `validate_data_coverage` and `validate_feature_integrity` already exist as stage surfaces
- feature construction is rich and mostly causal

## Current Weaknesses

- `errors="coerce"` is widely used without consistent run-level accounting
- data quality is checked in scattered ways rather than through one explicit contract
- feature definitions are powerful but not centrally registered
- feature drift is measurable only indirectly through downstream behavior

## First Sprint

### 1. Data quality surface

Add a central module:

- [project/core/data_quality.py](/home/tstuv/workspace/trading/EDGEE/project/core/data_quality.py)

Current scaffold covers:

- `missing_ratio`
- `outlier_ratio`
- `duplicate_timestamp_count`
- `timestamp_gap_count`
- `max_timestamp_gap_bars`
- `gap_ratio`
- `max_gap_len`
- `coerced_value_count`

### 2. Clean-stage wiring

Current scaffold integration:

- [build_cleaned_bars.py](/home/tstuv/workspace/trading/EDGEE/project/pipelines/clean/build_cleaned_bars.py)
- [validate_data_coverage.py](/home/tstuv/workspace/trading/EDGEE/project/pipelines/clean/validate_data_coverage.py)

The first pass should:

- compute quality metrics once per cleaned symbol slice
- store them in stage stats
- fail the coverage stage on obvious integrity breaks

Current status:

- clean stages now emit dedicated JSON reports under `data/reports/data_quality/<run_id>/cleaned/...`
- coverage validation now emits a validation report under `data/reports/data_quality/<run_id>/validation/...`
- warning thresholds and failure thresholds are now separate so drift can be visible without blocking every run

### 3. Feature registry surface

Add a central module:

- [project/core/feature_registry.py](/home/tstuv/workspace/trading/EDGEE/project/core/feature_registry.py)

The first pass should register the highest-impact core features:

- `basis_bps`
- `basis_zscore`
- `spread_bps`
- `spread_zscore`
- `rv_96`
- `rv_pct_17280`
- `funding_rate_scaled`
- `funding_abs_pct`
- `imbalance`
- `micro_depth_depletion`

Current status:

- core feature definitions are registered in code
- market-context state features are now registered as well
- market-context builds now emit dedicated JSON reports under `data/reports/context_quality/<run_id>/...`
- downstream detector guards now consume context confidence/entropy for canonical `ms_*` states in the volatility, liquidity, temporal, OI, basis, trend, and exhaustion families
- research hypothesis context filtering now also uses context confidence/entropy when the paired `ms_*` quality columns are present
- search evaluation now supports explicit hard-label vs confidence-aware context comparisons via the evaluator context-quality toggle
- canonical state-guard helpers now live in `project/features/context_guards.py`
- feature builds now emit dedicated JSON reports under `data/reports/feature_quality/<run_id>/...`
- feature-integrity validation now emits a matching validation report under `data/reports/feature_quality/<run_id>/validation/...`
- operator-facing feature catalog now exists in [FEATURE_CATALOG.md](/home/tstuv/workspace/trading/EDGEE/docs/FEATURE_CATALOG.md)

### 4. Feature-stage adoption

Feature builders should ensure the registry is loaded before downstream consumers inspect it.

Current target:

- [build_features.py](/home/tstuv/workspace/trading/EDGEE/project/pipelines/features/build_features.py)

## Recommended Next Iterations

### Data layer

1. Count coercions explicitly during ingest and clean, not just at summary time.
2. Emit per-column null-rate and coercion-rate diagnostics.
3. Add a dedicated data-quality artifact path under `data/reports/`.

### Feature layer

1. Add feature lineage metadata to manifests.
2. Emit per-feature drift and null diagnostics.
3. Reduce duplicate rolling/z-score logic across detectors and stages by routing through canonical feature definitions.

## Definition Of Done For This Track

This track is done only when:

- data quality is measured at the stage boundary
- feature definitions are centrally discoverable
- major data problems fail before detector stages
- small data drift becomes visible before it changes research outcomes
