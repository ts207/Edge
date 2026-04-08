# Discovery Benchmarks

## Overview
This document explains the benchmark configurations, thresholds, and review processes for the discovery layer.

## Current State

The benchmark control plane currently lives behind the Make targets and scripts that exist in this repo:

- `make benchmark-core`
- `make benchmark-review`
- `make benchmark-certify`
- `make benchmark-maintenance-smoke`
- `make benchmark-maintenance`

`make benchmark-m0` is retained only as a deprecated stub that exits with guidance to use `benchmark-core`.

## Ownership model

The benchmark stack has two layers:

- `project/research/benchmarks/discovery_benchmark.py`: The **execution adapter** for discovery benchmark comparison runs.
- `project/research/services/benchmark_matrix_service.py`, `benchmark_governance_service.py`, and `benchmark_review_service.py`: The **benchmark control plane**.

The execution adapter runs benchmark cases. The control plane defines, classifies, reviews, and governs them.

## Discovery mode maturity

| Mode | Status | Purpose |
| --- | --- | --- |
| `legacy` | **STABLE** | Abs t-stat ranking baseline. |
| `v2` | **STABLE-INTERNAL** | Canonical quality score (Significance + Tradability). |
| `ledger` | **EXPERIMENTAL** | V3 concept burden adjustment (Multiplicity). |
| `hierarchical` | **EXPERIMENTAL** | Hierarchical search-space pruning and staged discovery expansion. |
| `diversified` | **EXPERIMENTAL** | Diversity-aware shortlist selection layered on hierarchical search. |

## What benchmark evidence is expected to prove

The discovery benchmark layer is used to answer:

- whether discovery v2 improves promotion density near the top of the ranking
- whether discovery v2 reduces placebo-like top candidates
- whether discovery v2 improves top-rank tradability
- whether discovery v2 improves diversity and reduces structural overlap

Benchmark results do not automatically justify enabling experimental modes by default.

## Benchmark Presets
Presets are fixed combinations of slices and discovery modes.
- **core_v1**: The canonical preset evaluating multiple modes across 5 benchmark slices (`m0` to `m4`).

## Modes
Fixed discovery modes ensure comparability.
- `baseline_flat`: Flat search, basic scoring.
- `folds_plus_ledger`: Repeated walkforward with ledger.
- `hierarchical_v1`: Hierarchical search.
- `hierarchical_plus_diversified`: Hierarchical search with diversification selection.

## Metrics
- **Efficiency**: `candidate_count_generated`, `wall_clock_seconds`
- **Quality**: `top_n_median_after_cost_expectancy_bps`, `top_n_median_fold_sign_consistency`
- **Distinctness**: `shortlist_avg_similarity`, `shortlist_distinct_lineage_count`

## Thresholds
Explicit thresholds define PASS/WARN/FAIL states for benchmark slices.
See `project/configs/benchmarks/discovery/thresholds_v1.yaml`.

## Review Flow
1. Run Matrix: `make benchmark-core`
2. Review Results: `make benchmark-review`
3. Certify: `make benchmark-certify`

## Generated Outputs

The review/certification scripts write benchmark artifacts under `data/` and surface the operator-facing summary through `project/scripts/show_benchmark_review.py`.

Benchmark evidence is advisory until it is folded back into the canonical discovery defaults and verification policy.
