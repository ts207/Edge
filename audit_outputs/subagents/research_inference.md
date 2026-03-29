# research_inference

## Scope
- project/research/search/
- project/research/validation/
- project/research/promotion/
- project/research/services/
- project/research/robustness/
- project/research/agent_io/
- project/tests/research/
- project/tests/eval/
- project/tests/regressions/

## Summary
Discovery translation starts in project/research/agent_io/*, moves through candidate_discovery_service and candidate_discovery_scoring, uses project/research/search/evaluator.py for scoring, project/research/validation/* for splits/falsification/multiplicity/bundles, and promotion_service / confirmatory services for promotion and rerun comparison.

## Findings
### Search evaluator counts validation events whose forward-return horizon exits in the test split
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/search/search_feature_utils.py, project/research/search/evaluator.py
- Evidence: search_feature_utils assigns split_label by row timestamp only, and evaluate_hypothesis_batch() classifies observations from the entry bar label even when the realized forward-return window crosses into test bars.
- Why it matters: Holdout statistics can incorporate future test data while still being labeled as validation, biasing discovery and promotion evidence.
- Validation: Create a synthetic feature frame with an event near the validation/test boundary and a long horizon, then inspect validation_n_obs/test_n_obs from evaluate_hypothesis_batch().
- Remediation: Use event-window-aware split assignment or drop events whose realized horizon crosses a split boundary.

### Shift placebo construction uses the previous event timestamp instead of a true bar-offset timestamp
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/validation/falsification.py, project/research/services/candidate_discovery_scoring.py
- Evidence: generate_placebo_events() uses ts.shift(shift_bars), which reuses earlier timestamps instead of adding a bar-duration offset.
- Why it matters: The placebo no longer represents a bar-shift null and can duplicate real event timing structure.
- Validation: Call generate_placebo_events() on a simple timestamp series and compare output timestamps to a true one-bar time offset.
- Remediation: Shift by bar-duration or bar index, not by previous-row timestamp reuse.

### Confirmatory placebo pass/fail can be driven by train rows because placebo frames are not restricted to evaluation splits
- Severity: high
- Confidence: verified
- Category: statistical_integrity
- Affected: project/research/services/candidate_discovery_scoring.py
- Evidence: _build_confirmatory_evidence() filters the observed frame to evaluation rows, but _placebo_pass() is fed full placebo frames and ignores their split labels.
- Why it matters: Discovery-vs-confirmatory separation collapses inside the falsification path.
- Validation: Construct an eval-only observed frame and a train-only placebo frame, then call _placebo_pass() or _build_confirmatory_evidence() and observe the train placebo drives the result.
- Remediation: Filter placebo frames to evaluation rows before placebo gating.

### Run comparison treats explicit zero-valued split knobs as unavailable instead of mismatches
- Severity: high
- Confidence: verified
- Category: contract_integrity
- Affected: project/research/services/run_comparison_service.py
- Evidence: _build_run_comparison_compatibility() only flags mismatch when compared values are both > 0, so 0 vs 1 or 0 vs 5 is treated as unavailable rather than incompatible.
- Why it matters: Runs with materially different purge/embargo/entry-lag contracts can compare as compatible.
- Validation: Pass manifests with purge_bars=0 vs 5 or entry_lag_bars=0 vs 1 into _build_run_comparison_compatibility().
- Remediation: Treat explicit zero as meaningful and compare presence separately from value.

### Promotion output assembly can silently drop malformed evidence bundles without failing closed
- Severity: medium
- Confidence: likely
- Category: artifact_integrity
- Affected: project/research/services/promotion_service.py
- Evidence: execute_promotion() skips blank or malformed evidence_bundle_json values and writes the surviving subset without a parity check against promoted rows.
- Why it matters: A promoted candidate can survive while its evidence bundle artifact is missing or malformed.
- Validation: Feed execute_promotion() a promoted row with malformed evidence_bundle_json and inspect whether it still exits successfully with an incomplete evidence_bundles.jsonl.
- Remediation: Make promotion assembly fail when promoted rows lack valid evidence bundles, or emit a blocking integrity error on count mismatch.

### Confirmatory candidate matching only preserves economic identity when optional fields happen to be present
- Severity: medium
- Confidence: likely
- Category: economic_realism
- Affected: project/research/services/confirmatory_candidate_service.py
- Evidence: Base structural matching omits cost_config_digest, after_cost_includes_funding_carry, and cost_model_source unless those columns are populated in both compared artifacts.
- Why it matters: Two runs can match as structurally continuous without proving they used the same cost contract.
- Validation: Compare origin and target candidate artifacts with identical base keys but missing cost identity fields.
- Remediation: Promote economic-identity fields from optional to required for confirmatory matching, or downgrade comparisons to non-confirmatory when they are absent.
