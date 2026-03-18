# Benchmark Triage Guide

This document defines what to do when a maintained benchmark slice fails certification or regresses.

## Certification Failure Types

### `low_status`
- **Meaning**: The slice status dropped below the required floor (e.g., `informative` -> `foundation_only`).
- **Action**: 
  1. Check `context_mode_comparison.json` for evaluated row counts.
  2. If `evaluated_rows` is 0, the search space or event detector may be broken for this window.
  3. Verify that detector truth exists in `data/events/<run_id>/`.

### `low_foundation` / `blocked_foundation`
- **Meaning**: The live data foundation is `blocked` or dropped below the required readiness.
- **Action**:
  1. Inspect `live_data_foundation_report.json` for `missing_reports` or `validation_failure_count`.
  2. If reports are missing, check if the upstream pipeline stages (e.g., `build_cleaned_5m`, `build_features_5m`) failed.
  3. If issues are in `feature_quality`, investigate specific features with high `null_rate` or `constant_rate`.

### `status_regression`
- **Meaning**: Current status is weaker than the prior verified baseline.
- **Action**:
  1. Compare `current_review.json` vs `prior_review.json`.
  2. Look for changes in `selection_changed` or `selection_outcome_changed`.
  3. Check if a code change in the detector or evaluator caused the regression.

### `sample_collapse`
- **Meaning**: Evaluated rows dropped by more than 20% compared to baseline.
- **Action**:
  1. This usually indicates a change in event detection logic or stricter context quality filtering.
  2. Compare `hard_evaluated_rows` vs `confidence_evaluated_rows` to see if the collapse is context-driven.

## Priority Family Triage

### `STATISTICAL_DISLOCATION`
- Ensure `ZSCORE_STRETCH` coverage remains stable. 
- If sample size collapses, check basis/funding feature integrity.

### `VOLATILITY_TRANSITION`
- `VOL_SHOCK` should be robust.
- Foundation readiness must be `warn` or `ready`.

### `LIQUIDITY_DISLOCATION`
- `LIQUIDITY_GAP_PRINT` requires microstructure feature coverage.
- If foundation is blocked, check `depth_usd` and `spread_bps` health.

## Failure Escalation Policy

When a family's benchmark status shifts, follow this escalation path:

- **Certified -> Degraded** (e.g., `informative` -> `coverage_limited`)
  - **Impact**: Promotion is blocked for this family.
  - **Action**: File a defect in `defect_ledger.md`. Fix must be prioritized in the next research sprint.
  
- **Degraded -> Failed** (e.g., `coverage_limited` -> `foundation_only` with blocked readiness)
  - **Impact**: Severe platform regression.
  - **Action**: Immediate halt on all research for this family. Revert recent code changes or escalate to architectural review.

- **Informative -> Empty** (e.g., `hard_evaluated_rows` drops to 0)
  - **Impact**: Detector broken or search space missing events.
  - **Action**: Urgent fix required. Debug the `phase2` search engine output for that specific benchmark run.

## Reporting a Regression

If a regression is real (system-driven) and cannot be immediate fixed:
1. Document the finding in `defect_ledger.md`.
2. Propose an update to `benchmark_acceptance_thresholds.yaml` if the floor was too high.
3. Rerun the matrix and establish a new "downgraded" baseline only if approved.
