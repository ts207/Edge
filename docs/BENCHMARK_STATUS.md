# Benchmark Status

This document records which benchmark slices are currently authoritative, which are baseline-only, and which are coverage-limited.

Use it with [Research Operator Playbook](./RESEARCH_OPERATOR_PLAYBOOK.md), not instead of it.

## Current Verified Baseline

The latest verified maintained benchmark rerun is available at:

- review artifact: [data/reports/benchmarks/latest/benchmark_review.json](../data/reports/benchmarks/latest/benchmark_review.json)
- summary artifact: [data/reports/benchmarks/latest/benchmark_summary.json](../data/reports/benchmarks/latest/benchmark_summary.json)
- certification artifact: [data/reports/benchmarks/latest/benchmark_certification.json](../data/reports/benchmarks/latest/benchmark_certification.json)

### Quick Terminal Review

Use the operator script for a quick terminal summary of the latest maintained review and certification:

```bash
PYTHONPATH=. python3 project/scripts/show_benchmark_review.py
```

### Unified Maintenance Cycle

To rebuild the benchmark matrix and certify the results in one command:

```bash
PYTHONPATH=. python3 project/scripts/run_benchmark_maintenance_cycle.py
```

Results are archived in `data/reports/benchmarks/history/` and linked to `data/reports/benchmarks/latest/`.

### Governance and Triage

Maintainers should follow the [Benchmark Governance Runbook](./BENCHMARK_GOVERNANCE_RUNBOOK.md) for standard workflows.
Follow the [Benchmark Triage Guide](./BENCHMARK_TRIAGE.md) when certification fails.
Per-slice acceptance floors are codified in [benchmark_acceptance_thresholds.yaml](../spec/benchmarks/benchmark_acceptance_thresholds.yaml).

That rerun produced this current maintained status mix:

- `informative = 5`
- `quality_boundary = 1`

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
  - report locations:
    - `data/reports/context_mode_comparison/bench_vol_shock_btc_2024q1/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_vol_shock_btc_2024q1/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Informative Live Statistical-Dislocation Slice

- `ZSCORE_STRETCH`
  - run: `bench_zscore_stretch_btc_2025jan`
  - spec: [search_benchmark_zscore_stretch_live.yaml](../spec/search/search_benchmark_zscore_stretch_live.yaml)
  - status: `informative`
  - why: now the maintained live statistical-dislocation comparison slice
  - report locations:
    - `data/reports/context_mode_comparison/bench_zscore_stretch_btc_2025jan/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_zscore_stretch_btc_2025jan/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Informative Live Liquidity-Dislocation Slice

- `LIQUIDITY_GAP_PRINT`
  - run: `bench_liq_gap_btc_2025jan`
  - spec: [search_benchmark_liquidity_gap.yaml](../spec/search/search_benchmark_liquidity_gap.yaml)
  - status: `informative`
  - why: first maintained live liquidity-dislocation comparison slice
  - report locations:
    - `data/reports/context_mode_comparison/bench_liq_gap_btc_2025jan/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_liq_gap_btc_2025jan/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Informative Live Positioning-Extremes Slice

- `OI_SPIKE_POSITIVE`
  - run: `bench_positioning_btc_2025jan`
  - spec: [search_benchmark_positioning.yaml](../spec/search/search_benchmark_positioning.yaml)
  - status: `informative`
  - why: first maintained live positioning-extremes comparison slice
  - report locations:
    - `data/reports/context_mode_comparison/bench_positioning_btc_2025jan/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_positioning_btc_2025jan/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Informative Live Execution-Friction Slice

- `SPREAD_BLOWOUT`
  - run: `bench_execution_btc_2025jan`
  - spec: [search_benchmark_execution.yaml](../spec/search/search_benchmark_execution.yaml)
  - status: `informative`
  - why: first maintained live execution-friction comparison slice
  - report locations:
    - `data/reports/context_mode_comparison/bench_execution_btc_2025jan/context_mode_comparison.json`
    - `data/reports/live_foundation/bench_execution_btc_2025jan/perp/BTCUSDT/5m/live_data_foundation_report.json`

### Quality-Boundary Comparison Slice

- `FALSE_BREAKOUT`
  - run: `bench_false_breakout_btc_2024q1`
  - spec: [search_benchmark_false_breakout_quality_boundary.yaml](../spec/search/search_benchmark_false_breakout_quality_boundary.yaml)
  - status: `quality_boundary`
  - why: maintained decision-boundary slice for context-quality demotion checks
  - report location:
    - `data/reports/context_mode_comparison/bench_false_breakout_btc_2024q1/context_mode_comparison.json`

### Maintained Synthetic Statistical-Dislocation Comparison Slice

- `BASIS_DISLOC`
  - run: `synthetic_2025_full_year_v9`
  - spec: [search_benchmark_basis_disloc_synth.yaml](../spec/search/search_benchmark_basis_disloc_synth.yaml)
  - status: maintained synthetic authority for statistical-dislocation comparison
  - report location:
    - `data/reports/context_mode_comparison/synth_basis_disloc_2025_full_year_v9/context_mode_comparison.json`

### Retired Live Comparison Slot

- `FND_DISLOC`
  - prior run: `bench_fnd_disloc_btc_2024q1`
  - current policy: retired from maintained matrix; superseded by `ZSCORE_STRETCH`

## Operator Rule

When a new agent needs one benchmark per class:

1. start with the latest verified matrix review artifact under `data/reports/benchmarks/latest/`
2. use `VOL_SHOCK` for non-empty live context-comparison behavior in the volatility family
3. use `ZSCORE_STRETCH` for the maintained live statistical-dislocation comparison slice
4. use `LIQUIDITY_GAP_PRINT` for the maintained live liquidity-dislocation comparison slice
5. use `OI_SPIKE_POSITIVE` for the maintained live positioning-extremes comparison slice
6. use `SPREAD_BLOWOUT` for the maintained live execution-friction comparison slice
7. use `FALSE_BREAKOUT` quality-boundary for confidence-aware demotion behavior
8. use synthetic `BASIS_DISLOC` as the maintained synthetic statistical-dislocation authority
9. do not route new operator work through live `FND_DISLOC` unless you are explicitly investigating that retired slot

## Current Coverage Boundary

- the maintained set covers: `stability`, `quality-boundary demotion`, and `statistical-dislocation comparison`
- the maintained set does NOT currently cover: `selection_changed = true` (cases where confidence-aware mode changes the winning hypothesis_id)

## Platform Strategy Shift

Effort is shifting from searching for selection flips in BTC history to broader live historical coverage:
- focus on `LIQUIDITY_DISLOCATION`, `POSITIONING_EXTREMES`, and `EXECUTION_FRICTION` families
- expand beyond BTC-first coverage
- revisit selection-flip search only after new live data or materially different regime definitions are introduced

## Current Bottom Line

Right now the maintained benchmark set answers four different operator questions:

- `VOL_SHOCK`: what does a non-empty live hard-label vs confidence-aware comparison look like when the selected hypothesis survives both modes
- `ZSCORE_STRETCH`: what does the maintained live statistical-dislocation comparison surface look like under the current quality-artifact contract
- `FALSE_BREAKOUT`: what does a real confidence-aware quality boundary look like when the selected hypothesis stays the same but falls below the benchmark validity floor
- `BASIS_DISLOC`: what the maintained synthetic statistical-dislocation comparison baseline looks like when you need a controlled comparison authority for that family
