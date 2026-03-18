# Technical Debt & Architectural Audit

This document records dead code, redundant logic, architectural scaffolding, and suspicious behaviors identified during the Deep Audit of March 2026.

---

## 1. Dead Code & Utility Scripts

| Finding ID | Artifact / Path | Description | Risk |
| :--- | :--- | :--- | :--- |
| **DC-001** | `project/scripts/tmp_debug_eval.py` | One-off debugging script. No callers in repo. | Zero |
| **DC-002** | `docs/plans/` (Legacy) | Plans from 2025/early 2026 that are 100% implemented. | Zero |

## 2. Redundant Logic & Architectural Scaffolding

| Finding ID | Artifact / Path | Description | Impact |
| :--- | :--- | :--- | :--- |
| **RL-001** | `project/pipelines/features/build_context_features.py` | Identity pass that only moves data from `features/` to `context_features/`. | High IO Waste |
| **RL-002** | `ms_roll_24`, `ms_amihud_24`, `ms_kyle_24`, `ms_vpin_24` | Microstructure features computed in `build_features.py` but consumed by zero detectors. | ~15% Storage Bloat |
| **RL-003** | `BaseOIShockDetector`, `BaseFundingDetector` | Fragmented base classes with duplicated logic across `families/` and `detectors/`. | High Maintenance |

## 3. Legacy Infrastructure & Migration Guards

| Finding ID | Artifact / Path | Description | Target Disposition |
| :--- | :--- | :--- | :--- |
| **LI-001** | `project/strategy/runtime/` | Legacy runtime namespace. Overlaps with `project/strategy/runtime`. | Consolidation |
| **LI-002** | `tests/test_legacy_wrapper_packages_removed.py` | Meta-test verifying package deletion. | Removal |
| **LI-003** | `project/events/detectors/legacy_aliases.py` | Registry bloat for renamed events. | In-place consolidation |

## 4. Logical Traps & Suspicious Behaviors

| Finding ID | Description | Root Cause | Risk |
| :--- | :--- | :--- | :--- |
| **LT-001** | Redundant Market States | `low_liquidity_state` and `aftershock_state` are highly correlated, creating redundant hypotheses. | Diluted Alpha Significance |
| **LT-002** | Distribution Mismatch (OI) | 1m vs 5m Open Interest data sources (API vs Archive) create inconsistent features. | Model Instability |
| **LT-003** | Future Lookahead (PIT Violation) | `FeeRegimeChangeDetector` uses `shift(-1)`, making it unusable for live trading. | Backtest Leakage |
| **LT-004** | Inconsistent Signal Precedence | `ScheduledNewsDetector` ignores spec parameters if *any* news-related column is present. | Undocumented Logic |
| **LT-005** | Borderline PIT Risk (Unshifted Quantiles) | Several detectors use `rolling().quantile()` without `shift(1)`, potentially leaking data from the current bar's close into its own trigger logic. | Subtle Optimization Bias |

## 5. Implementation Redundancy (Code Duplication)

| Finding ID | Artifact / Path | Description | Impact |
| :--- | :--- | :--- | :--- |
| **RD-001** | `project/execution/backtest/engine.py` | Compat wrapper for `project/engine/runner.py`. | Unnecessary Facade |
| **RD-002** | `project/execution/runtime/dsl_interpreter.py` | Compat wrapper for `project/strategy/runtime`. | Unnecessary Facade |
| **RD-003** | `detect_temporal_family` (temporal.py) | Manual wrapping of registry logic that already exists in `registry.py`. | Maintenance Overhead |
| **RD-004** | `core.py` vs `promotion_core.py` | Split promotion logic across files with nearly identical names. | High Developer Friction |
| **RD-005** | `validation.py` vs `sanity.py` | Overlapping validation primitives (timestamps, schema checks). | Logic Fragmentation |

## 6. Testing Scaffolding & Meta-Tests

| Finding ID | Artifact / Path | Description | Risk |
| :--- | :--- | :--- | :--- |
| **TS-001** | `tests/compat/` | Verification that legacy surfaces are gone. | CI Noise |
| **TS-002** | `tests/test_no_legacy_wrapper_imports.py` | Checks for top-level imports that are already blocked by ruff. | Redundant Linting |
| **TS-003** | `tests/scripts/test_review_tool_history.sh` | Shell script testing a python tool; redundant with pytest. | Fragility |

## 7. Statistical Fragility & Research Bias

| Finding ID | Description | Root Cause | Risk |
| :--- | :--- | :--- | :--- |
| **SF-001** | Normality Assumptions | `basis_zscore` and `spread_zscore` use standard rolling std dev, assuming Gaussian distributions. | Signal Distortion in Fat-Tails |
| **SF-002** | Hardcoded Alpha (0.05) | Multiple testing correction and drift detection use a fixed 0.05 p-value. | Type-I Error Sprawl |
| **SF-003** | Simplified Overlap Correction | `evaluate_hypothesis_batch` uses a density-based heuristic for overlap rather than full Newey-West per hypothesis. | Overstated T-Stats |
| **SF-004** | Weighted Variance Sensitivity | `weighted_std` in evaluator uses reliability weights which can become unstable with extreme weights. | Outlier-Driven Invalidation |

## 8. Structural Limits & Scaling Bottlenecks

| Finding ID | Description | Root Cause | Impact |
| :--- | :--- | :--- | :--- |
| **SL-001** | OOM Risk (Forking) | `distributed_runner.py` relies on `fork` copy-on-write. As workers modify memory, the full feature table is duplicated per process. | OOM on 100+ Symbol Runs |
| **SL-002** | Python-Loop Position Compilation | `compiler.py` uses a standard for-loop for position generation. | Evaluation Bottleneck |
| **SL-003** | Synchronous DAG | Pipeline stages execute sequentially per run_id. | Under-utilization of HW |
| **SL-004** | Rigid Schema Hardcoding | `feature_schema_v2` is hardcoded as a default in scripts and manifests. | Schema Evolution Friction |

## 9. Infra & Portfolio Limits

| Finding ID | Description | Root Cause | Risk |
| :--- | :--- | :--- | :--- |
| **IP-001** | Hardcoded Concentration Cap | `concentration_cap` is hardcoded to 5% of portfolio value in `sizing.py`. | Inflexible Risk Management |
| **IP-002** | Kelly Multiplier Clip | `confidence_multiplier` is hardcoded to a max of 5.0. | Hidden Leverage Limit |
| **IP-003** | Redundant run_all Facade | `project/infra/orchestration/run_all.py` is a 3rd wrapper for the same entry point. | Scaffolding Overload |
