# Benchmark Status

This document records which benchmark slices are currently authoritative, which are baseline-only, and which are coverage-limited.

Use it with [Research Operator Playbook](./RESEARCH_OPERATOR_PLAYBOOK.md), not instead of it.

## Current Verified Baseline

The latest verified maintained benchmark rerun is:

- review artifact: [/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_review.json](/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_review.json)
- summary artifact: [/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_summary.json](/tmp/benchmark_research_family_v1_post_zscore_20260318/benchmark_summary.json)

That rerun produced this current maintained status mix:

- `informative = 2`
- `quality_boundary = 1`

Use that review artifact as the concrete starting point for operator interpretation, then drill into the per-slice reports below.

## How To Read This

- `authoritative`: maintained slice with a real artifact surface worth using for operator decisions
- `informative`: maintained slice is non-empty and useful, but does not currently produce a stronger decision boundary than the authoritative slice
- `quality_boundary`: maintained slice where confidence-aware context changes the benchmark decision outcome, even if the winning hypothesis id does not change
- `foundation_only`: use for live-data readiness and contract checks, not for maintained context-comparison conclusions
- `coverage_limited`: do not treat as a maintained comparison benchmark yet

## Current Maintained Status

### Informative Live Comparison Slice

- `VOL_SHOCK`
  - run: `bench_vol_shock_btc_2024q1`
  - spec: [search_benchmark_vol_shock.yaml](../spec/search/search_benchmark_vol_shock.yaml)
  - status: `informative`
  - why: live BTC 2024Q1 slice produces a real non-empty hard-label vs confidence-aware comparison artifact and a maintained live-foundation report
  - current verified result: same selected hypothesis remains valid in both modes, with confidence-aware context reducing usable support
  - report locations:
    - `data/reports/context_mode_comparison/bench_vol_shock_btc_2024q1/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_vol_shock_btc_2024q1/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Informative Live Statistical-Dislocation Slice

- `ZSCORE_STRETCH`
  - run: `bench_zscore_stretch_btc_2025jan`
  - spec: [search_benchmark_zscore_stretch_live.yaml](../spec/search/search_benchmark_zscore_stretch_live.yaml)
  - status: `informative`
  - why:
    - current-contract BTC January 2025 live run produces a non-empty comparison artifact
    - live foundation is `warn`, not `blocked`
    - this is now the maintained live statistical-dislocation comparison slice
  - current verified result:
    - both hard-label and confidence-aware modes evaluate rows
    - `selection_changed = false`
    - `selection_outcome_changed = false`
  - report locations:
    - `data/reports/context_mode_comparison/bench_zscore_stretch_btc_2025jan/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_zscore_stretch_btc_2025jan/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Quality-Boundary Comparison Slice

- `FALSE_BREAKOUT`
  - run: `bench_false_breakout_btc_2024q1`
  - spec: [search_benchmark_false_breakout_quality_boundary.yaml](../spec/search/search_benchmark_false_breakout_quality_boundary.yaml)
  - status: `quality_boundary`
  - why: with `min_sample_size = 34`, hard-label mode keeps the selected candidate valid while confidence-aware mode demotes the same selected hypothesis below the sample floor
  - interpretation: this is a maintained decision-boundary slice, not just a sample-count delta slice
  - current verified result: same selected hypothesis id, but different benchmark decision outcome
  - report location:
    - `data/reports/context_mode_comparison/bench_false_breakout_btc_2024q1/context_mode_comparison.json`

### Maintained Synthetic Statistical-Dislocation Comparison Slice

- `BASIS_DISLOC`
  - run: `synthetic_2025_full_year_v9`
  - spec: [search_benchmark_basis_disloc_synth.yaml](../spec/search/search_benchmark_basis_disloc_synth.yaml)
  - status: maintained synthetic authority for statistical-dislocation comparison
  - why: this slice remains the clean synthetic comparison baseline for the family even after the live `ZSCORE_STRETCH` promotion
  - report location:
    - `data/reports/context_mode_comparison/synth_basis_disloc_2025_full_year_v9/context_mode_comparison.json`

### Retired Live Comparison Slot

- `FND_DISLOC`
  - prior run: `bench_fnd_disloc_btc_2024q1`
  - prior status: `foundation_only`
  - current policy:
    - no longer part of the maintained matrix
    - do not use it as the maintained live statistical-dislocation comparison benchmark
  - why: `ZSCORE_STRETCH` on BTC January 2025 now provides a stronger current-contract live comparison surface

## Operator Rule

When a new agent needs one benchmark per class:

1. start with the latest verified matrix review artifact under `/tmp/benchmark_research_family_v1_post_zscore_20260318/`
2. use `VOL_SHOCK` for non-empty live context-comparison behavior in the volatility family
3. use `ZSCORE_STRETCH` for the maintained live statistical-dislocation comparison slice
4. use `FALSE_BREAKOUT` quality-boundary for confidence-aware demotion behavior
5. use synthetic `BASIS_DISLOC` as the maintained synthetic statistical-dislocation authority
6. do not route new operator work through live `FND_DISLOC` unless you are explicitly investigating that retired slot

## Current Bottom Line

Right now the maintained benchmark set answers four different operator questions:

- `VOL_SHOCK`: what does a non-empty live hard-label vs confidence-aware comparison look like when the selected hypothesis survives both modes
- `ZSCORE_STRETCH`: what does the maintained live statistical-dislocation comparison surface look like under the current quality-artifact contract
- `FALSE_BREAKOUT`: what does a real confidence-aware quality boundary look like when the selected hypothesis stays the same but falls below the benchmark validity floor
- `BASIS_DISLOC`: what the maintained synthetic statistical-dislocation comparison baseline looks like when you need a controlled comparison authority for that family
